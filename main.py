import os
import time
import shutil
import threading
import uuid
import datetime
import random
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
st.set_page_config(page_title="FB Sticker Force-Sender", layout="wide")

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
            "last_action": "Starting...",
            "start_time": datetime.datetime.now().strftime("%I:%M %p")
        }
        return tid

    def get_task(self, tid):
        return self.tasks.get(tid)

    def update_log(self, tid, msg):
        if tid in self.tasks:
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            self.tasks[tid]["logs"].append(f"[{timestamp}] {msg}")
            self.tasks[tid]["last_action"] = msg

manager = GlobalTaskManager()

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    
    service = Service(shutil.which("chromedriver") or "/usr/bin/chromedriver")
    try:
        return webdriver.Chrome(service=service, options=chrome_options)
    except:
        return None

def sticker_sender_logic(driver, tid):
    try:
        wait = WebDriverWait(driver, 15)
        
        # 1. Click Sticker Icon
        selectors = [
            "//div[@aria-label='Choose a sticker']",
            "//div[@aria-label='Stickers']",
            "//div[contains(@aria-label, 'sticker') and @role='button']"
        ]
        
        btn = None
        for sel in selectors:
            try:
                btn = wait.until(EC.presence_of_element_located((By.XPATH, sel)))
                if btn: break
            except: continue
            
        if btn:
            # Force click using JS to avoid 'not interactable' error
            driver.execute_script("arguments[0].click();", btn)
            manager.update_log(tid, "Sticker panel opened (JS Click)")
            time.sleep(5) # Give it time to load stickers
            
            # 2. Find All Sticker Images (specifically inside the grid)
            # Facebook often uses images or spans for stickers
            stickers = driver.find_elements(By.CSS_SELECTOR, "div[role='gridcell'] img, div[aria-label='Stickers'] img")
            
            if stickers:
                # Filter visible stickers
                target = random.choice(stickers[:min(len(stickers), 15)])
                
                manager.update_log(tid, "Forcing sticker selection...")
                
                # FIX: Use JavaScript to click the image if it's "not interactable"
                driver.execute_script("arguments[0].scrollIntoView(true);", target)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", target)
                
                # Extra precaution: Press Enter
                ActionChains(driver).send_keys(Keys.ENTER).perform()
                return True
            else:
                manager.update_log(tid, "Stickers visible nahi ho rahe. Refreshing...")
        return False
    except Exception as e:
        manager.update_log(tid, f"Interaction Error: {str(e)[:50]}")
        return False

def background_worker(tid, cookie_str, url, delay, infinite):
    driver = get_driver()
    if not driver:
        manager.tasks[tid]["status"] = "Driver Error"
        return

    try:
        manager.update_log(tid, "Injecting Cookies...")
        driver.get("https://www.facebook.com")
        for c in cookie_str.split(';'):
            if '=' in c:
                name, val = c.strip().split('=', 1)
                driver.add_cookie({'name': name.strip(), 'value': val.strip(), 'domain': '.facebook.com'})
        
        manager.update_log(tid, "Opening Chat...")
        driver.get(url)
        time.sleep(12) # Full load time
        
        manager.tasks[tid]["status"] = "Running ✅"

        while not manager.tasks[tid]["stop"]:
            success = sticker_sender_logic(driver, tid)
            
            if success:
                manager.tasks[tid]["count"] += 1
                manager.update_log(tid, f"✅ Done! Sent #{manager.tasks[tid]['count']}")
            else:
                manager.update_log(tid, "Send failed. Retrying in 10s...")
                driver.refresh()
                time.sleep(10)

            if not infinite: break
            time.sleep(delay + random.randint(3, 7))

    except Exception as e:
        manager.update_log(tid, f"System Crash: {str(e)}")
    finally:
        driver.quit()
        if tid in manager.tasks:
            manager.tasks[tid]["status"] = "Task Finished"

# --- STREAMLIT UI ---
st.title("🚀 FB Sticker Pro (Force Click Mode)")

c1, c2 = st.columns([1, 2])

with c1:
    st.subheader("Config")
    ck = st.text_area("Cookies", height=100)
    url = st.text_input("Messenger Link")
    wait_time = st.slider("Delay", 10, 300, 20)
    loop = st.toggle("Repeat", value=True)
    
    if st.button("Start Now", use_container_width=True):
        if ck and url:
            tid = manager.create_task()
            threading.Thread(target=background_worker, args=(tid, ck, url, wait_time, loop)).start()
            st.success(f"ID: {tid}")

with c2:
    search = st.text_input("Track ID").upper()
    if search:
        data = manager.get_task(search)
        if data:
            col_a, col_b = st.columns(2)
            col_a.metric("Sent", data["count"])
            col_b.metric("Status", data["status"])
            st.write(f"**Last Action:** `{data['last_action']}`")
            st.code("\n".join(data["logs"][-15:]))
            if st.button("Stop"): data["stop"] = True
            
