import os
import time
import shutil
import threading
import uuid
import datetime
import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

# --- PAGE CONFIG ---
st.set_page_config(page_title="UltraStable FB Sender", layout="wide")
st.title("🚀 Pro Background Messenger")

# --- GLOBAL TASK MANAGER ---
@st.cache_resource
class TaskManager:
    def __init__(self):
        self.tasks = {}

    def create_task(self):
        task_id = str(uuid.uuid4())[:6].upper()
        self.tasks[task_id] = {
            "status": "Running",
            "logs": [],
            "count": 0,
            "stop": False,
            "start_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        return task_id

    def log_update(self, task_id, message):
        if task_id in self.tasks:
            timestamp = datetime.datetime.now().strftime("%H:%M")
            # Circular log: Keep only last 50 entries to save memory
            self.tasks[task_id]["logs"] = (self.tasks[task_id]["logs"] + [f"[{timestamp}] {message}"]) [-50:]

    def stop_task(self, task_id):
        if task_id in self.tasks:
            self.tasks[task_id]["stop"] = True
            self.tasks[task_id]["status"] = "Manual Stop"

manager = TaskManager()

# --- OPTIMIZED DRIVER ---
def get_optimized_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new") # Faster headless mode
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--blink-settings=imagesEnabled=false") # Don't load images (Save RAM)
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Auto-detect paths
    paths = ["/usr/bin/chromedriver", "/usr/local/bin/chromedriver"]
    driver_path = next((p for p in paths if os.path.exists(p)), shutil.which("chromedriver"))
    
    try:
        service = Service(driver_path) if driver_path else Service()
        return webdriver.Chrome(service=service, options=chrome_options)
    except:
        return None

# --- BACKGROUND WORKER ---
def run_stable_task(task_id, cookie_str, url, msg, delay, is_infinite):
    manager.log_update(task_id, "System Initializing...")
    driver = get_optimized_driver()
    
    if not driver:
        manager.log_update(task_id, "CRITICAL: Driver failure.")
        manager.tasks[task_id]["status"] = "Driver Error"
        return

    try:
        # Load FB
        driver.get("https://www.facebook.com/")
        
        # Inject Cookies
        for item in cookie_str.split(';'):
            if '=' in item:
                name, val = item.strip().split('=', 1)
                driver.add_cookie({'name': name, 'value': val, 'domain': '.facebook.com'})
        
        driver.get(url)
        time.sleep(10) # Initial load wait
        
        while not manager.tasks[task_id]["stop"]:
            try:
                # 1. Look for message box
                selectors = ['div[aria-label="Message"]', 'div[role="textbox"]', '[contenteditable="true"]']
                msg_box = None
                for s in selectors:
                    try:
                        msg_box = driver.find_element(By.CSS_SELECTOR, s)
                        if msg_box: break
                    except: continue

                if msg_box:
                    # Clear and Send
                    driver.execute_script("arguments[0].focus();", msg_box)
                    ActionChains(driver).send_keys(msg).send_keys(Keys.RETURN).perform()
                    
                    manager.tasks[task_id]["count"] += 1
                    manager.log_update(task_id, f"Success | Total: {manager.tasks[task_id]['count']}")
                    
                    if not is_infinite: break
                    time.sleep(delay)
                else:
                    manager.log_update(task_id, "Waiting for chat to load...")
                    driver.refresh() # Refresh if stuck
                    time.sleep(15)

            except Exception as e:
                manager.log_update(task_id, f"Retrying... (Network/FB Lag)")
                time.sleep(10)

    except Exception as e:
        manager.log_update(task_id, f"Fatal Error: {str(e)[:50]}")
    finally:
        driver.quit()
        if not manager.tasks[task_id]["stop"]:
            manager.tasks[task_id]["status"] = "Completed/Idle"

# --- UI ---
t1, t2 = st.tabs(["⚡ Deployment", "📊 Live Monitor"])

with t1:
    col1, col2 = st.columns([2, 1])
    with col1:
        c_input = st.text_area("Session Cookies", placeholder="c_user=...; xs=...", height=100)
        u_input = st.text_input("Target URL", "https://www.facebook.com/messages/t/...")
    with col2:
        m_input = st.text_input("Message Content", "Hello!")
        d_input = st.number_input("Interval (Seconds)", 5, 3600, 30)
        inf_mode = st.checkbox("Keep running forever", True)

    if st.button("🚀 Deploy to Background"):
        if c_input and u_input:
            tid = manager.create_task()
            threading.Thread(target=run_stable_task, args=(tid, c_input, u_input, m_input, d_input, inf_mode), daemon=True).start()
            st.success(f"Deployment Successful! ID: {tid}")
        else:
            st.warning("Data missing.")

with t2:
    search_id = st.text_input("Enter Active ID to Monitor")
    if search_id:
        data = manager.get_task(search_id)
        if data:
            c1, c2, c3 = st.columns(3)
            c1.metric("Status", data["status"])
            c2.metric("Sent", data["count"])
            c3.metric("Started", data["start_time"])
            
            st.code("\n".join(data["logs"]))
            
            if st.button("🔴 Kill Process"):
                manager.stop_task(search_id)
                st.rerun()
        else:
            st.error("ID not found.")
    
