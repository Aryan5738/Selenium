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
st.set_page_config(page_title="FB Force Sticker Pro", layout="wide")

@st.cache_resource
class GlobalTaskManager:
    def __init__(self):
        self.tasks = {}

    def create_task(self):
        tid = str(uuid.uuid4())[:6].upper()
        self.tasks[tid] = {
            "status": "Initializing...",
            "logs": [],
            "count": 0,
            "stop": False,
            "last_screenshot": None,
            "start_time": datetime.datetime.now().strftime("%I:%M %p")
        }
        return tid

    def get_task(self, tid):
        return self.tasks.get(tid)

    def update_log(self, tid, msg, driver=None):
        if tid in self.tasks:
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            self.tasks[tid]["logs"].append(f"[{timestamp}] {msg}")
            if driver:
                try:
                    screenshot = driver.get_screenshot_as_base64()
                    self.tasks[tid]["last_screenshot"] = screenshot
                except: pass

manager = GlobalTaskManager()

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1280,1024")
    service = Service(shutil.which("chromedriver") or "/usr/bin/chromedriver")
    try:
        return webdriver.Chrome(service=service, options=chrome_options)
    except: return None

def send_sticker_pro(driver, tid):
    try:
        wait = WebDriverWait(driver, 15)
        
        # 1. Click Sticker Icon (Multiple Selectors for Backup)
        manager.update_log(tid, "Searching for sticker icon...")
        icon_xpath = "//div[@aria-label='Choose a sticker'] | //div[@aria-label='Stickers'] | //div[@role='button'][descendant::i[contains(@style, 'stickers')]]"
        
        sticker_btn = wait.until(EC.presence_of_element_located((By.XPATH, icon_xpath)))
        driver.execute_script("arguments[0].scrollIntoView(true);", sticker_btn)
        time.sleep(1)
        driver.execute_script("arguments[0].click();", sticker_btn)
        
        manager.update_log(tid, "Icon clicked. Waiting for panel...", driver)
        time.sleep(6) # Increased wait for panel loading

        # 2. Find Stickers inside the grid
        # FB stickers are usually inside gridcells or have a specific data-visual-completion
        stickers = driver.find_elements(By.CSS_SELECTOR, "div[role='gridcell'] img, img[src*='sticker'], div[aria-label='Stickers'] img")
        
        if stickers:
            target = random.choice(stickers[:min(len(stickers), 12)])
            manager.update_log(tid, f"Found {len(stickers)} stickers. Sending one...", driver)
            
            # Click the sticker
            driver.execute_script("arguments[0].click();", target)
            
            # Confirm with Enter just in case
            time.sleep(1)
            ActionChains(driver).send_keys(Keys.ENTER).perform()
            return True
        else:
            manager.update_log(tid, "Stickers not found in panel. Panel blank?", driver)
            return False
            
    except Exception as e:
        manager.update_log(tid, f"Error: {str(e)[:50]}", driver)
        return False

def background_worker(tid, cookie_str, url, delay, infinite):
    driver = get_driver()
    if not driver:
        manager.tasks[tid]["status"] = "Driver Failure"
        return

    try:
        driver.get("https://www.facebook.com")
        for c in cookie_str.split(';'):
            if '=' in c:
                name, val = c.strip().split('=', 1)
                driver.add_cookie({'name': name.strip(), 'value': val.strip(), 'domain': '.facebook.com'})
        
        driver.get(url)
        time.sleep(12)
        manager.tasks[tid]["status"] = "Running ✅"

        while not manager.tasks[tid]["stop"]:
            success = send_sticker_pro(driver, tid)
            if success:
                manager.tasks[tid]["count"] += 1
                manager.update_log(tid, f"✅ Sticker #{manager.tasks[tid]['count']} delivered.")
            else:
                manager.update_log(tid, "Send failed. Refreshing page...")
                driver.refresh()
                time.sleep(10)

            if not infinite: break
            time.sleep(delay + random.randint(2, 5))

    except Exception as e:
        manager.update_log(tid, f"Fatal: {str(e)}")
    finally:
        driver.quit()
        if tid in manager.tasks: manager.tasks[tid]["status"] = "Finished"

# --- UI ---
st.title("🛡️ FB Ultra Force-Sticker (Live Preview)")

c1, c2 = st.columns([1, 2])

with c1:
    ck = st.text_area("Cookies")
    url = st.text_input("Messenger Link")
    delay = st.slider("Wait Time", 10, 300, 20)
    if st.button("🚀 Start Bot"):
        tid = manager.create_task()
        threading.Thread(target=background_worker, args=(tid, ck, url, delay, True)).start()
        st.success(f"Task ID: {tid}")

with c2:
    search = st.text_input("Monitor Task (Enter ID)").upper()
    if search:
        data = manager.get_task(search)
        if data:
            st.metric("Sent Count", data["count"])
            st.write(f"Status: {data['status']}")
            
            # --- SCREENSHOT VIEW ---
            if data["last_screenshot"]:
                st.subheader("📸 Live Browser View")
                st.image(base64.b64decode(data["last_screenshot"]), caption="Yahan dikhega browser mein kya ho raha hai", use_container_width=True)
            
            with st.expander("Logs"):
                st.code("\n".join(data["logs"][-10:]))
            if st.button("Stop"): data["stop"] = True
        
