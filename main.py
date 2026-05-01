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
st.set_page_config(page_title="FB Ultimate Jugad", layout="wide")

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
    chrome_options.add_argument("--window-size=1920,1080")
    service = Service(shutil.which("chromedriver") or "/usr/bin/chromedriver")
    return webdriver.Chrome(service=service, options=chrome_options)

def clean_e2ee_popups(driver, tid):
    """PIN aur Restore wale popups ko hatane ke liye"""
    popups = [
        "//div[@role='dialog']//div[@aria-label='Close']",
        "//span[contains(text(), 'restore')]",
        "//div[@aria-label='Don’t restore messages']"
    ]
    for p in popups:
        try:
            btns = driver.find_elements(By.XPATH, p)
            for b in btns:
                if b.is_displayed():
                    driver.execute_script("arguments[0].click();", b)
                    time.sleep(2)
        except: pass

def send_sticker_ultimate_jugad(driver, tid):
    try:
        wait = WebDriverWait(driver, 12)
        clean_e2ee_popups(driver, tid)

        # 1. Open Sticker Icon
        icon_xpath = "//div[@aria-label='Choose a sticker'] | //div[@role='button']//i[contains(@style, 'stickers')]"
        sticker_btn = wait.until(EC.presence_of_element_located((By.XPATH, icon_xpath)))
        
        # JS Click for opening panel
        driver.execute_script("arguments[0].click();", sticker_btn)
        manager.update_log(tid, "Sticker panel opened. Scanning grid...", driver)
        time.sleep(6) # Waiting for full decryption of stickers

        # 2. Advanced Multi-Click & Keyboard Jugad
        stickers = driver.find_elements(By.CSS_SELECTOR, "div[role='gridcell'] img, img[alt*='sticker'], div[aria-label='Stickers'] img")
        
        if stickers:
            target = random.choice(stickers[:min(len(stickers), 10)])
            manager.update_log(tid, "Sticker Targeted! Applying Force Send...", driver)
            
            # ActionChains Complex Jugad
            actions = ActionChains(driver)
            
            # Move to sticker, Click and Hold, then Release
            actions.move_to_element(target).click_and_hold(target).pause(1).release(target).perform()
            
            # Second Method: JS Force Click
            driver.execute_script("arguments[0].click();", target)
            
            # Third Method: Keyboard Force
            time.sleep(1)
            actions.send_keys(Keys.ENTER).perform()
            actions.send_keys(Keys.RETURN).perform() # Double Enter for E2EE
            
            return True
        return False
    except Exception as e:
        manager.update_log(tid, "Wait... Element not found yet.", driver)
        return False

def worker(tid, cookies, url, delay):
    driver = get_driver()
    try:
        driver.get("https://www.facebook.com")
        for c in cookies.split(';'):
            if '=' in c:
                n, v = c.strip().split('=', 1)
                driver.add_cookie({'name': n.strip(), 'value': v.strip(), 'domain': '.facebook.com'})
        
        manager.update_log(tid, f"Locking Chat: {url}")
        driver.get(url)
        time.sleep(12)
        
        manager.tasks[tid]["status"] = "Running ✅"

        while not manager.tasks[tid]["stop"]:
            # URL Lock Check
            if driver.current_url != url:
                driver.get(url)
                time.sleep(8)

            if send_sticker_ultimate_jugad(driver, tid):
                manager.tasks[tid]["count"] += 1
                manager.update_log(tid, f"✅ Done! #{manager.tasks[tid]['count']} sent.")
            else:
                driver.refresh()
                time.sleep(10)

            time.sleep(delay + random.randint(2, 5))
    finally:
        driver.quit()
        if tid in manager.tasks: manager.tasks[tid]["status"] = "Stopped"

# --- UI ---
st.title("🛡️ FB E2EE Ultimate Jugad Bot")
c1, c2 = st.columns([1, 2])

with c1:
    ck = st.text_area("Cookies")
    chat_url = st.text_input("Target URL (E2EE Link)")
    wait_time = st.slider("Wait Between Stickers", 5, 300, 15)
    if st.button("🚀 Launch Jugad Bot"):
        tid = manager.create_task()
        threading.Thread(target=worker, args=(tid, ck, chat_url, wait_time)).start()
        st.success(f"ID: {tid}")

with c2:
    search = st.text_input("Monitor ID").upper()
    if search:
        data = manager.get_task(search)
        if data:
            st.metric("Total Sent", data["count"])
            if data["last_screenshot"]:
                st.image(base64.b64decode(data["last_screenshot"]), caption="Jugad View (Live)")
            st.code("\n".join(data["logs"][-15:]))
            if st.button("Stop"): data["stop"] = True
        
