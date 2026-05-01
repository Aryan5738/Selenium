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
st.set_page_config(page_title="FB Terminator Sticker", layout="wide")

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

def clean_e2ee_trash(driver, tid):
    """PIN aur 'Restore' popups ko clean karne ke liye"""
    trash = [
        "//div[@role='dialog']//div[@aria-label='Close']",
        "//span[contains(text(), 'restore')]",
        "//div[@aria-label='Don’t restore messages']"
    ]
    for p in trash:
        try:
            btns = driver.find_elements(By.XPATH, p)
            for b in btns:
                if b.is_displayed():
                    driver.execute_script("arguments[0].click();", b)
                    time.sleep(2)
        except: pass

def terminator_sticker_send(driver, tid):
    try:
        wait = WebDriverWait(driver, 15)
        clean_e2ee_trash(driver, tid)

        # 1. Open Sticker Panel (Force JS + Hover)
        icon_xpath = "//div[@aria-label='Choose a sticker'] | //div[@role='button']//i[contains(@style, 'stickers')]"
        sticker_btn = wait.until(EC.presence_of_element_located((By.XPATH, icon_xpath)))
        
        actions = ActionChains(driver)
        actions.move_to_element(sticker_btn).pause(1).click().perform()
        driver.execute_script("arguments[0].click();", sticker_btn)
        
        manager.update_log(tid, "Sticker panel opened. Scanning grid...", driver)
        time.sleep(7) 

        # 2. Hardcore Sticker Selection (Coordinates & Offsets)
        # Targeted selectors specifically for E2EE grid
        stickers = driver.find_elements(By.CSS_SELECTOR, "div[role='gridcell'] img, img[alt*='sticker']")
        
        if stickers:
            # Picking a fresh target
            target = random.choice(stickers[:min(len(stickers), 12)])
            manager.update_log(tid, "Sticker targeted. Executing Mouse Simulation...", driver)
            
            # --- THE TERMINATOR JUGAD ---
            # Method 1: Move mouse to center of element and click manually
            actions.move_to_element(target).click_and_hold().pause(1.5).release().perform()
            
            # Method 2: Click with slight offset (1px right, 1px down) to bypass bot detection
            try:
                actions.move_to_element_with_offset(target, 1, 1).click().perform()
            except: pass
            
            # Method 3: JS Direct dispatch event (Fake human click)
            driver.execute_script("""
                var ev = new MouseEvent('click', {
                    'view': window,
                    'bubbles': true,
                    'cancelable': true
                });
                arguments[0].dispatchEvent(ev);
            """, target)
            
            # Method 4: Double Enter Force
            time.sleep(1)
            actions.send_keys(Keys.ENTER).perform()
            actions.send_keys(Keys.ENTER).perform() 
            
            return True
        return False
    except Exception as e:
        manager.update_log(tid, "UI is sluggish. Syncing...", driver)
        return False

def worker(tid, cookies, url, delay):
    driver = get_driver()
    try:
        # Pre-login steps
        driver.get("https://www.facebook.com")
        for c in cookies.split(';'):
            if '=' in c:
                n, v = c.strip().split('=', 1)
                driver.add_cookie({'name': n.strip(), 'value': v.strip(), 'domain': '.facebook.com'})
        
        driver.get(url)
        time.sleep(12)
        manager.tasks[tid]["status"] = "Running ✅"

        while not manager.tasks[tid]["stop"]:
            # URL enforcement
            if driver.current_url != url:
                driver.get(url)
                time.sleep(8)

            if terminator_sticker_send(driver, tid):
                manager.tasks[tid]["count"] += 1
                manager.update_log(tid, f"✅ Sticker #{manager.tasks[tid]['count']} Sent", driver)
            else:
                manager.update_log(tid, "Failed to interact. Refreshing UI...", driver)
                driver.refresh()
                time.sleep(10)

            time.sleep(delay + random.randint(3, 8))
    finally:
        driver.quit()
        if tid in manager.tasks: manager.tasks[tid]["status"] = "Stopped"

# --- STREAMLIT INTERFACE ---
st.title("🦾 FB E2EE Terminator Bot (Hard-Click Mode)")
col1, col2 = st.columns([1, 2])

with col1:
    ck = st.text_area("Cookies")
    chat_url = st.text_input("E2EE Target URL")
    wait_time = st.slider("Interval (Sec)", 5, 300, 20)
    if st.button("🚀 Start Terminator Bot"):
        tid = manager.create_task()
        threading.Thread(target=worker, args=(tid, ck, chat_url, wait_time)).start()
        st.success(f"ID: {tid}")

with col2:
    search = st.text_input("Monitor ID").upper()
    if search and manager.get_task(search):
        data = manager.get_task(search)
        st.metric("Total Sent", data["count"])
        if data["last_screenshot"]:
            st.image(base64.b64decode(data["last_screenshot"]), caption="Terminator View (Live)")
        st.code("\n".join(data["logs"][-15:]))
        if st.button("Stop"): data["stop"] = True
                                        
