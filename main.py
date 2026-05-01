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
st.set_page_config(page_title="FB UID Sticker Pro", layout="wide")

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

def send_sticker_force(driver, tid):
    try:
        wait = WebDriverWait(driver, 12)
        
        # 1. Click Sticker Icon (Supports both Full Messenger & Chat Pop-up)
        manager.update_log(tid, "Searching for sticker icon...")
        icon_xpath = (
            "//div[@aria-label='Choose a sticker'] | "
            "//div[@aria-label='Stickers'] | "
            "//div[@role='button']//i[contains(@style, 'stickers')]"
        )
        
        sticker_btn = wait.until(EC.presence_of_element_located((By.XPATH, icon_xpath)))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", sticker_btn)
        time.sleep(1)
        driver.execute_script("arguments[0].click();", sticker_btn)
        
        manager.update_log(tid, "Sticker panel opened. Waiting for load...", driver)
        time.sleep(6) # Essential wait for stickers to appear

        # 2. Find and Click a Sticker
        # Targeted selectors for modern FB structure
        stickers = driver.find_elements(By.CSS_SELECTOR, "div[role='gridcell'] img, img[src*='sticker'], div[aria-label='Stickers'] img")
        
        if stickers:
            target = random.choice(stickers[:min(len(stickers), 15)])
            manager.update_log(tid, f"Sending sticker variation...", driver)
            
            # Click and confirm
            driver.execute_script("arguments[0].click();", target)
            time.sleep(1)
            ActionChains(driver).send_keys(Keys.ENTER).perform()
            return True
        else:
            manager.update_log(tid, "No stickers found in the panel.", driver)
            return False
            
    except Exception as e:
        manager.update_log(tid, f"Error: {str(e)[:40]}", driver)
        return False

def background_worker(tid, cookie_str, target_val, delay, infinite):
    driver = get_driver()
    if not driver:
        manager.tasks[tid]["status"] = "Driver Failure"
        return

    try:
        # Build URL automatically
        # Agar numeric hai toh /messages/t/ format, agar username hai toh direct profile chat
        if target_val.isdigit():
            final_url = f"https://www.facebook.com/messages/t/{target_val}"
        else:
            final_url = f"https://www.facebook.com/{target_val}"
            
        manager.update_log(tid, f"Target set to: {final_url}")
        
        driver.get("https://www.facebook.com")
        for c in cookie_str.split(';'):
            if '=' in c:
                name, val = c.strip().split('=', 1)
                driver.add_cookie({'name': name.strip(), 'value': val.strip(), 'domain': '.facebook.com'})
        
        driver.get(final_url)
        time.sleep(10)
        manager.tasks[tid]["status"] = "Running ✅"

        while not manager.tasks[tid]["stop"]:
            success = send_sticker_force(driver, tid)
            if success:
                manager.tasks[tid]["count"] += 1
                manager.update_log(tid, f"✅ Done! Total: {manager.tasks[tid]['count']}")
            else:
                manager.update_log(tid, "Retrying page refresh...")
                driver.refresh()
                time.sleep(8)

            if not infinite: break
            time.sleep(delay + random.randint(3, 8))

    except Exception as e:
        manager.update_log(tid, f"Fatal Error: {str(e)}")
    finally:
        driver.quit()
        if tid in manager.tasks: manager.tasks[tid]["status"] = "Stopped"

# --- UI ---
st.title("🛡️ FB UID/Username Sticker Pro")

c1, c2 = st.columns([1, 2])

with c1:
    st.markdown("### ⚙️ Configuration")
    ck = st.text_area("Cookies", placeholder="c_user=...; xs=...")
    target_id = st.text_input("Target UID or Username", placeholder="e.g. 1000456... or babiie.king")
    wait_time = st.slider("Interval (Sec)", 10, 300, 25)
    
    if st.button("🚀 Start Sending"):
        if ck and target_id:
            tid = manager.create_task()
            threading.Thread(target=background_worker, args=(tid, ck, target_id, wait_time, True)).start()
            st.success(f"Started! Tracking ID: {tid}")

with c2:
    search = st.text_input("Enter ID to Monitor").upper()
    if search:
        data = manager.get_task(search)
        if data:
            st.metric("Sent Stickers", data["count"])
            if data["last_screenshot"]:
                st.image(base64.b64decode(data["last_screenshot"]), caption="Live Preview", use_container_width=True)
            st.code("\n".join(data["logs"][-12:]))
            if st.button("Stop"): data["stop"] = True
                
