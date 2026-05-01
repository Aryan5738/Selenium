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
st.set_page_config(page_title="FB Ultra Multi-Sticker", layout="wide")

# CSS for better UI
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 10px; border: 1px solid #3e445e; }
    </style>
    """, unsafe_allow_html=True)

# --- TASK MANAGER (Thread Safe) ---
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
            "last_action": "Starting engine...",
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

# --- SELENIUM CORE ---
def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    
    # Path for Streamlit Cloud
    service = Service(shutil.which("chromedriver") or "/usr/bin/chromedriver")
    try:
        return webdriver.Chrome(service=service, options=chrome_options)
    except:
        return None

def sticker_sender_logic(driver, tid):
    try:
        wait = WebDriverWait(driver, 15)
        
        # 1. Look for Sticker Icon
        selectors = [
            "//div[@aria-label='Choose a sticker']",
            "//div[@aria-label='Stickers']",
            "//span[contains(@class, 'x10l6tqk')]//div[@role='button']"
        ]
        
        btn = None
        for sel in selectors:
            try:
                btn = wait.until(EC.element_to_be_clickable((By.XPATH, sel)))
                if btn: break
            except: continue
            
        if btn:
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(4) # Waiting for stickers to load
            
            # 2. Find All Sticker Images
            stickers = driver.find_elements(By.CSS_SELECTOR, "div[role='gridcell'] img, img[src*='sticker']")
            
            if stickers:
                # Select a random sticker from the first 20 available
                target = random.choice(stickers[:min(len(stickers), 20)])
                
                # Human-like Click
                actions = ActionChains(driver)
                actions.move_to_element(target).click().perform()
                
                # Force Send with Enter
                time.sleep(1)
                actions.send_keys(Keys.ENTER).perform()
                return True
        return False
    except Exception as e:
        manager.update_log(tid, f"Send Error: {str(e)[:50]}")
        return False

# --- BACKGROUND WORKER ---
def background_worker(tid, cookie_str, url, delay, infinite):
    driver = get_driver()
    if not driver:
        manager.tasks[tid]["status"] = "Driver Error (Check logs)"
        return

    try:
        manager.update_log(tid, "Logging into Facebook...")
        driver.get("https://www.facebook.com")
        
        # Add Cookies
        for c in cookie_str.split(';'):
            if '=' in c:
                name, val = c.strip().split('=', 1)
                driver.add_cookie({'name': name, 'value': val, 'domain': '.facebook.com'})
        
        manager.update_log(tid, "Navigating to Chat URL...")
        driver.get(url)
        time.sleep(10)
        
        manager.tasks[tid]["status"] = "Running ✅"

        while not manager.tasks[tid]["stop"]:
            success = sticker_sender_logic(driver, tid)
            
            if success:
                manager.tasks[tid]["count"] += 1
                manager.update_log(tid, f"Success! Sticker #{manager.tasks[tid]['count']} sent.")
            else:
                manager.update_log(tid, "Sticker not sent. Refreshing page...")
                driver.refresh()
                time.sleep(10)

            if not infinite: break
            time.sleep(delay + random.randint(2, 5))

    except Exception as e:
        manager.update_log(tid, f"Fatal Error: {str(e)}")
    finally:
        driver.quit()
        if tid in manager.tasks:
            manager.tasks[tid]["status"] = "Stopped/Finished"

# --- STREAMLIT UI ---
st.title("🤖 FB Multi-Sticker Automation")

col_setup, col_status = st.columns([1, 2])

with col_setup:
    st.subheader("🛠️ Setup Task")
    ck = st.text_area("FB Cookies", height=120, placeholder="Paste your cookies here...")
    chat = st.text_input("Messenger URL")
    wait_time = st.slider("Delay (Seconds)", 5, 300, 20)
    mode = st.toggle("Infinite Loop", value=True)
    
    if st.button("🚀 Launch Task", use_container_width=True):
        if ck and chat:
            new_id = manager.create_task()
            t = threading.Thread(target=background_worker, args=(new_id, ck, chat, wait_time, mode))
            t.start()
            st.success(f"Task Started! ID: **{new_id}**")
            st.info("Note: Copy the ID above to track progress.")
        else:
            st.warning("Please fill all fields.")

with col_status:
    st.subheader("📊 Live Tracking")
    search_id = st.text_input("Enter Task ID to Monitor").upper()
    
    if search_id:
        task_data = manager.get_task(search_id)
        
        if task_data:
            # Stats Grid
            m1, m2, m3 = st.columns(3)
            m1.metric("Current Status", task_data["status"])
            m2.metric("Sent Count", task_data["count"])
            m3.metric("Start Time", task_data["start_time"])
            
            st.markdown(f"**Current Action:** `{task_data['last_action']}`")
            
            # Logs Area
            with st.expander("View Full Execution Logs", expanded=True):
                if task_data["logs"]:
                    st.code("\n".join(task_data["logs"][-15:]))
                else:
                    st.write("No logs yet...")
            
            # Control
            if task_data["status"] == "Running ✅":
                if st.button("🛑 Stop Task", type="primary", use_container_width=True):
                    task_data["stop"] = True
                    st.rerun()
        else:
            st.error("❌ Invalid ID or Server Restarted. Data for this ID is gone.")
                 
