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
st.set_page_config(page_title="FB E2EE Popup Fixer", layout="wide")

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

# --- POPUP CRUSHER (DEEP CLEAN) ---
def crush_blocking_popups(driver, tid):
    try:
        # Step 1: Sabse pehle PIN wala close (X) dhoondhein
        pin_x = driver.find_elements(By.XPATH, "//div[@role='dialog']//div[@aria-label='Close']")
        for x in pin_x:
            if x.is_displayed():
                driver.execute_script("arguments[0].click();", x)
                time.sleep(2)

        # Step 2: "Don't restore messages" (Aapke screenshot wala main dushman)
        # Iske liye hum text aur aria-label dono target karenge
        restore_selectors = [
            "//span[text()='Don’t restore messages']",
            "//div[@aria-label='Don’t restore messages']",
            "//div[@role='button']//span[contains(text(), 'restore')]",
            "//button[contains(., 'Don')]"
        ]
        
        for sel in restore_selectors:
            btns = driver.find_elements(By.XPATH, sel)
            for b in btns:
                if b.is_displayed():
                    manager.update_log(tid, "🎯 Clicking 'Don't Restore' button...", driver)
                    # Force JavaScript Click
                    driver.execute_script("arguments[0].click();", b)
                    time.sleep(3)
                    return True
        return False
    except:
        return False

def send_sticker_force_mode(driver, tid, target_url):
    try:
        # URL Lock Check
        if driver.current_url != target_url:
            driver.get(target_url)
            time.sleep(5)

        # Crush Popups before any action
        crush_blocking_popups(driver, tid)

        wait = WebDriverWait(driver, 10)
        
        # 1. Open Sticker Panel
        icon_xpath = "//div[@aria-label='Choose a sticker'] | //div[@role='button']//i[contains(@style, 'stickers')]"
        sticker_btn = wait.until(EC.presence_of_element_located((By.XPATH, icon_xpath)))
        driver.execute_script("arguments[0].click();", sticker_btn)
        
        manager.update_log(tid, "Sticker panel opened.", driver)
        time.sleep(5) 

        # 2. Multi-Sticker Selection
        stickers = driver.find_elements(By.CSS_SELECTOR, "div[role='gridcell'] img, img[alt*='sticker']")
        if stickers:
            target = random.choice(stickers[:min(len(stickers), 15)])
            manager.update_log(tid, "Sticker found! Double-burst clicking...", driver)
            
            # JavaScript Burst Click (Fix for "Not Interactable")
            driver.execute_script("arguments[0].click();", target)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", target)
            
            # ActionChain Enter
            ActionChains(driver).send_keys(Keys.ENTER).perform()
            return True
        
        # Agar panel khula hai par stickers nahi mile, toh ho sakta hai popup wapas aa gaya ho
        crush_blocking_popups(driver, tid)
        return False
    except Exception as e:
        manager.update_log(tid, "Syncing UI elements...", driver)
        return False

def background_worker(tid, cookies, url, delay):
    driver = get_driver()
    try:
        driver.get("https://www.facebook.com")
        for c in cookies.split(';'):
            if '=' in c:
                n, v = c.strip().split('=', 1)
                driver.add_cookie({'name': n.strip(), 'value': v.strip(), 'domain': '.facebook.com'})
        
        driver.get(url)
        time.sleep(15) 
        
        # Initial Clear
        crush_blocking_popups(driver, tid)
        
        manager.tasks[tid]["status"] = "Running ✅"

        while not manager.tasks[tid]["stop"]:
            success = send_sticker_force_mode(driver, tid, url)
            if success:
                manager.tasks[tid]["count"] += 1
                manager.update_log(tid, f"✅ Sticker #{manager.tasks[tid]['count']} sent.")
            else:
                # Agar fail ho raha hai toh popup check karke refresh karein
                crush_blocking_popups(driver, tid)
                driver.refresh()
                time.sleep(10)

            time.sleep(delay + random.randint(2, 5))
    finally:
        driver.quit()
        if tid in manager.tasks: manager.tasks[tid]["status"] = "Stopped"

# --- UI ---
st.title("🛡️ FB E2EE Popup Crusher Pro")
c1, c2 = st.columns([1, 2])

with c1:
    ck = st.text_area("Cookies")
    chat_url = st.text_input("E2EE Chat Link")
    wait_time = st.slider("Wait Between Stickers (Sec)", 10, 300, 20)
    if st.button("🚀 Start Ultimate Bot"):
        tid = manager.create_task()
        threading.Thread(target=background_worker, args=(tid, ck, chat_url, wait_time)).start()
        st.success(f"Task Started! ID: {tid}")

with c2:
    search = st.text_input("Monitor ID").upper()
    if search:
        data = manager.get_task(search)
        if data:
            st.metric("Sent Successfully", data["count"])
            if data["last_screenshot"]:
                st.image(base64.b64decode(data["last_screenshot"]), caption="Live Preview")
            st.code("\n".join(data["logs"][-12:]))
            if st.button("Stop"): data["stop"] = True
            
