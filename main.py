import os
import time
import shutil
import threading
import uuid
import datetime
import random
import base64
import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

# --- PAGE CONFIG ---
st.set_page_config(page_title="FB E2EE Master Bot", layout="wide")

@st.cache_resource
class GlobalTaskManager:
    def __init__(self):
        self.tasks = {}

    def create_task(self):
        tid = str(uuid.uuid4())[:6].upper()
        self.tasks[tid] = {"status": "Starting...", "logs": [], "count": 0, "stop": False, "last_screenshot": None}
        return tid

    def get_task(self, tid): return self.tasks.get(tid)

    def update_log(self, tid, msg, driver=None):
        if tid in self.tasks:
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            self.tasks[tid]["logs"].append(f"[{ts}] {msg}")
            if driver:
                try: self.tasks[tid]["last_screenshot"] = driver.get_screenshot_as_base64()
                except: pass

manager = GlobalTaskManager()

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1600,900")
    service = Service(shutil.which("chromedriver") or "/usr/bin/chromedriver")
    return webdriver.Chrome(service=service, options=chrome_options)

# --- THE CRUSHER: HANDLES PIN AND 'DON'T RESTORE' ---
def clean_e2ee_blocking_popups(driver, tid):
    try:
        # Step 1: Close the PIN Restore Popup (The (X) button)
        pin_xpaths = [
            "//div[@role='dialog']//div[@aria-label='Close']",
            "//div[@role='dialog']//i[contains(@class, 'x1b0065r')]",
            "//div[contains(@aria-label, 'PIN')]//div[@role='button']"
        ]
        for path in pin_xpaths:
            btns = driver.find_elements(By.XPATH, path)
            for btn in btns:
                if btn.is_displayed():
                    manager.update_log(tid, "Closing PIN popup...", driver)
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(3) # Wait for second popup

        # Step 2: Click "Don't restore messages" (The Blue/White button)
        restore_xpaths = [
            "//span[contains(text(), 'Don’t restore')]",
            "//span[contains(text(), 'restore messages')]",
            "//div[@role='button'][descendant::span[contains(text(), 'restore')]]",
            "//div[@aria-label='Don’t restore messages']"
        ]
        for path in restore_xpaths:
            btns = driver.find_elements(By.XPATH, path)
            for btn in btns:
                if btn.is_displayed():
                    manager.update_log(tid, "Clicking 'Don't Restore'...", driver)
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(4)
                    return True
        return False
    except:
        return False

def send_sticker_e2ee(driver, tid):
    try:
        wait = WebDriverWait(driver, 12)
        
        # Clean Popups
        clean_e2ee_blocking_popups(driver, tid)
        
        # 1. Sticker Icon
        icon_xpath = "//div[@aria-label='Choose a sticker'] | //div[@role='button']//i[contains(@style, 'stickers')]"
        sticker_btn = wait.until(EC.presence_of_element_located((By.XPATH, icon_xpath)))
        driver.execute_script("arguments[0].click();", sticker_btn)
        
        manager.update_log(tid, "Panel opened. Searching stickers...", driver)
        time.sleep(6) 

        # 2. Sticker Selection
        stickers = driver.find_elements(By.CSS_SELECTOR, "div[role='gridcell'] img, img[alt*='sticker']")
        if stickers:
            target = random.choice(stickers[:min(len(stickers), 10)])
            driver.execute_script("arguments[0].click();", target)
            time.sleep(1)
            # Final Force Send
            ActionChains(driver).send_keys(Keys.ENTER).perform()
            return True
        return False
    except Exception as e:
        manager.update_log(tid, "Scanning UI...", driver)
        return False

def worker(tid, cookies, url, delay):
    driver = get_driver()
    try:
        driver.get("https://www.facebook.com")
        for c in cookies.split(';'):
            if '=' in c:
                n, v = c.strip().split('=', 1)
                driver.add_cookie({'name': n.strip(), 'value': v.strip(), 'domain': '.facebook.com'})
        
        driver.get(url)
        time.sleep(15) 
        
        manager.tasks[tid]["status"] = "Running ✅"

        while not manager.tasks[tid]["stop"]:
            # Initial cleanup
            clean_e2ee_blocking_popups(driver, tid)
            
            if send_sticker_e2ee(driver, tid):
                manager.tasks[tid]["count"] += 1
                manager.update_log(tid, f"✅ Sent #{manager.tasks[tid]['count']}")
            else:
                driver.refresh()
                time.sleep(12)

            time.sleep(delay + random.randint(2, 5))
    finally:
        driver.quit()
        if tid in manager.tasks: manager.tasks[tid]["status"] = "Stopped"

# --- UI ---
st.title("🛡️ FB Master E2EE (Popup Crusher)")
c1, c2 = st.columns([1, 2])

with c1:
    ck = st.text_area("Cookies")
    chat_url = st.text_input("E2EE URL")
    wait_time = st.slider("Delay (Sec)", 10, 300, 25)
    if st.button("🚀 Start Bot"):
        tid = manager.create_task()
        threading.Thread(target=worker, args=(tid, ck, chat_url, wait_time)).start()
        st.success(f"ID: {tid}")

with c2:
    search = st.text_input("Track ID").upper()
    if search:
        data = manager.get_task(search)
        if data:
            st.metric("Sent", data["count"])
            if data["last_screenshot"]:
                st.image(base64.b64decode(data["last_screenshot"]), caption="Live Browser Screen")
            st.code("\n".join(data["logs"][-12:]))
            if st.button("Stop"): data["stop"] = True
