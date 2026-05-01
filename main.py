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
st.set_page_config(page_title="FB Sniper Sticker Bot", layout="wide")

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
    chrome_options.add_argument("--window-size=1920,1080") # Full HD for better precision
    service = Service(shutil.which("chromedriver") or "/usr/bin/chromedriver")
    return webdriver.Chrome(service=service, options=chrome_options)

def clean_and_lock_chat(driver, tid, target_url):
    """Chat lock aur Popups clean karne ke liye"""
    try:
        # 1. URL Enforcement (Galat chat fix)
        if driver.current_url != target_url:
            manager.update_log(tid, "Wrong chat detected! Re-locking to target...")
            driver.get(target_url)
            time.sleep(8)

        # 2. Popups Removal
        popups = [
            "//div[@role='dialog']//div[@aria-label='Close']",
            "//span[contains(text(), 'restore')]",
            "//div[@aria-label='Don’t restore messages']",
            "//div[@role='button']//span[text()='Cancel']"
        ]
        for p in popups:
            btns = driver.find_elements(By.XPATH, p)
            for b in btns:
                if b.is_displayed():
                    driver.execute_script("arguments[0].click();", b)
                    time.sleep(1)
    except: pass

def send_sticker_sniper_mode(driver, tid):
    try:
        wait = WebDriverWait(driver, 15)
        
        # 1. Open Sticker Panel
        icon_xpath = "//div[@aria-label='Choose a sticker'] | //div[@role='button']//i[contains(@style, 'stickers')]"
        sticker_btn = wait.until(EC.presence_of_element_located((By.XPATH, icon_xpath)))
        
        # Move mouse to icon first
        actions = ActionChains(driver)
        actions.move_to_element(sticker_btn).perform()
        time.sleep(1)
        driver.execute_script("arguments[0].click();", sticker_btn)
        
        manager.update_log(tid, "Sticker panel opened. Loading stickers...", driver)
        time.sleep(7) # Loading time for E2EE stickers

        # 2. Deep Sticker Selection (Sniper Click)
        # Targeted selector for the grid
        stickers = driver.find_elements(By.CSS_SELECTOR, "div[role='gridcell'] img, img[alt*='sticker']")
        
        if stickers:
            # Pick a random sticker from the visible ones
            target = random.choice(stickers[:min(len(stickers), 8)])
            manager.update_log(tid, "Targeting sticker with Multi-Method click...", driver)
            
            # Method 1: Scroll to View
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target)
            time.sleep(1)
            
            # Method 2: Mouse Hover + Click
            actions.move_to_element(target).click().perform()
            time.sleep(0.5)
            
            # Method 3: JS Force Click
            driver.execute_script("arguments[0].click();", target)
            
            # Method 4: Enter Key Confirmation
            actions.send_keys(Keys.ENTER).perform()
            
            return True
        return False
    except Exception as e:
        manager.update_log(tid, "Interface busy. Waiting...", driver)
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
        time.sleep(12)
        manager.tasks[tid]["status"] = "Running ✅"

        while not manager.tasks[tid]["stop"]:
            # Pehle chat lock aur popups saaf karo
            clean_and_lock_chat(driver, tid, url)
            
            if send_sticker_sniper_mode(driver, tid):
                manager.tasks[tid]["count"] += 1
                manager.update_log(tid, f"✅ Sniper Sent #{manager.tasks[tid]['count']}")
            else:
                driver.refresh()
                time.sleep(10)
            
            # Delay before next sticker
            time.sleep(delay + random.randint(3, 6))
    finally:
        driver.quit()
        if tid in manager.tasks: manager.tasks[tid]["status"] = "Stopped"

# --- UI ---
st.title("🎯 FB Sniper Sticker Bot (Full Advance)")
c1, c2 = st.columns([1, 2])

with c1:
    st.markdown("### 🛠️ Configuration")
    ck = st.text_area("Cookies")
    chat_url = st.text_input("Target Chat Link (Full URL)")
    wait_time = st.slider("Delay (Seconds)", 5, 300, 20)
    if st.button("🚀 Launch Sniper Bot"):
        if ck and chat_url:
            tid = manager.create_task()
            threading.Thread(target=worker, args=(tid, ck, chat_url, wait_time)).start()
            st.success(f"Task ID: {tid}")

with c2:
    search = st.text_input("Monitor ID").upper()
    if search:
        data = manager.get_task(search)
        if data:
            st.metric("Total Stickers Sent", data["count"])
            if data["last_screenshot"]:
                st.image(base64.b64decode(data["last_screenshot"]), caption="Sniper View (Live)")
            st.code("\n".join(data["logs"][-15:]))
            if st.button("Stop"): data["stop"] = True
            
