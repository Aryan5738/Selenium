import streamlit as st
import time
import requests
import json
import threading
import shutil
import os
import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

# --- 🔐 CONFIGURATION (Hardcoded) ---
FIXED_BIN_ID = "6942bb0eae596e708fa052f4" 
API_KEY = "$2a$10$6/uFXvi1Lj4R4wsWLipdz.QrNDGyB1RviPCZPFW0DIUmrrNBkLyiu"

# Headers for JSONBin
HEADERS = {
    "Content-Type": "application/json",
    "X-Master-Key": API_KEY
}
BASE_URL = f"https://api.jsonbin.io/v3/b/{FIXED_BIN_ID}"

# --- PAGE CONFIG ---
st.set_page_config(page_title="E2EE Auto-Server", layout="wide", page_icon="⚡")

# --- CUSTOM CSS (Modern UI) ---
st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: white; }
    .status-card { 
        background-color: #222831; 
        padding: 15px; 
        border-radius: 10px; 
        border-left: 5px solid #00ADB5; 
        margin-bottom: 10px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.5);
    }
    .running-badge {
        background-color: #00ADB5; color: white; padding: 2px 8px; border-radius: 5px; font-size: 0.8em;
    }
    .header-style {
        font-size: 24px; font-weight: bold; color: #00FFF5;
    }
</style>
""", unsafe_allow_html=True)

# --- DATABASE FUNCTIONS ---
def get_db():
    try:
        r = requests.get(BASE_URL + "/latest", headers=HEADERS)
        if r.status_code == 200:
            return r.json()['record']
        return {}
    except: return {}

def update_task_in_db(task_id, status, count, new_logs=None):
    """Updates only specific fields to avoid overwriting everything blindly"""
    try:
        # 1. Fetch Latest to preserve other users' data
        current_db = get_db()
        
        # 2. Check if Task Exists
        if task_id in current_db:
            current_db[task_id]["status"] = status
            current_db[task_id]["count"] = count
            current_db[task_id]["last_active"] = str(datetime.datetime.now())
            
            if new_logs:
                if "logs" not in current_db[task_id]: current_db[task_id]["logs"] = []
                current_db[task_id]["logs"].extend(new_logs)
                # Keep DB size small (Last 5 logs only)
                current_db[task_id]["logs"] = current_db[task_id]["logs"][-5:]
            
            # 3. Push Update
            requests.put(BASE_URL, headers=HEADERS, json=current_db)
    except Exception as e:
        print(f"DB Update Error: {e}")

# --- SELENIUM BOT ENGINE ---
def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    
    path_chromium = shutil.which("chromium") or "/usr/bin/chromium"
    path_driver = shutil.which("chromedriver") or "/usr/bin/chromedriver"

    if os.path.exists(path_chromium) and os.path.exists(path_driver):
        chrome_options.binary_location = path_chromium
        service = Service(path_driver)
        try:
            return webdriver.Chrome(service=service, options=chrome_options)
        except: return None
    return None

def worker_thread(task_id, task_data):
    """Background Thread for a Single User"""
    user_name = task_data.get('user', 'Anon')
    
    # Mark in DB that thread started
    update_task_in_db(task_id, "Initializing", 0, [f"Server accepted task for {user_name}"])
    
    driver = get_driver()
    if not driver:
        update_task_in_db(task_id, "Failed", 0, ["Driver Error"])
        return

    try:
        # 1. Login
        driver.get("https://www.facebook.com/")
        try:
            cookies = task_data['cookie'].split(';')
            for c in cookies:
                if '=' in c:
                    n, v = c.strip().split('=', 1)
                    driver.add_cookie({'name': n, 'value': v, 'domain': '.facebook.com'})
        except: pass

        # 2. Chat
        driver.get(task_data['url'])
        time.sleep(8)
        
        # 3. Popup Hunter
        try:
            btns = driver.find_elements(By.XPATH, "//div[@role='button']//span[contains(text(), 'Continue')]")
            for btn in btns: driver.execute_script("arguments[0].click();", btn)
        except: pass

        count = 0
        keep_running = True
        update_task_in_db(task_id, "Running", 0, ["Target Locked. Sending..."])

        while keep_running:
            # Check Stop Signal (Read DB every 5 messages to save bandwidth)
            if count % 5 == 0:
                fresh_data = get_db().get(task_id, {})
                if fresh_data.get("stop_signal", False):
                    update_task_in_db(task_id, "Stopped", count, ["Stop Signal Received"])
                    break

            try:
                # TYPE & SEND
                box = driver.find_element(By.CSS_SELECTOR, 'div[aria-label="Message"], div[role="textbox"]')
                driver.execute_script("arguments[0].focus();", box)
                actions = ActionChains(driver)
                actions.send_keys(task_data['msg'])
                actions.send_keys(Keys.RETURN)
                actions.perform()
                
                count += 1
                
                # Update Cloud every message
                update_task_in_db(task_id, "Running", count, [f"Msg #{count} Sent"])
                
                if not task_data.get('infinite', False):
                    update_task_in_db(task_id, "Completed", count, ["Task Done"])
                    keep_running = False
                else:
                    time.sleep(int(task_data.get('delay', 2)))
            except:
                time.sleep(5)
                # Retry Popups
                try:
                    btns = driver.find_elements(By.XPATH, "//div[@role='button']//span[contains(text(), 'Continue')]")
                    for btn in btns: driver.execute_script("arguments[0].click();", btn)
                except: pass

    except Exception as e:
        update_task_in_db(task_id, "Error", 0, [str(e)])
    finally:
        driver.quit()

# --- MAIN SERVER LOGIC ---

# Header
c1, c2 = st.columns([1, 4])
with c1:
    st.image("https://cdn-icons-png.flaticon.com/512/2111/2111615.png", width=80)
with c2:
    st.markdown("<div class='header-style'>⚡ E2EE AUTO-SERVER</div>", unsafe_allow_html=True)
    st.caption("✅ System Online & Listening automatically. Do not close this tab.")

st.divider()

# Status Container (Refreshes automatically)
status_container = st.empty()

# --- 🚀 AUTOMATIC LISTENING LOOP ---
# This loop runs immediately when the script loads. No buttons needed.
while True:
    try:
        # 1. Fetch All Tasks from Cloud
        db_data = get_db()
        
        # 2. Render UI Dashboard
        with status_container.container():
            if not db_data:
                st.info("Waiting for tasks... (Cloud Bridge Idle)")
            
            # Sort tasks (Running first)
            sorted_tasks = sorted(db_data.items(), key=lambda x: x[1].get("status") == "Running", reverse=True)

            active_threads = 0
            
            for task_id, info in sorted_tasks:
                status = info.get("status", "Unknown")
                user = info.get("user", "Anonymous")
                count = info.get("count", 0)
                logs = info.get("logs", [])
                last_log = logs[-1] if logs else "No logs"
                
                # Color Coding
                border_color = "#00ADB5" if status == "Running" else "#FF2E63"
                
                st.markdown(f"""
                <div style="background-color: #222831; padding: 10px; border-radius: 8px; border-left: 5px solid {border_color}; margin-bottom: 8px;">
                    <div style="display: flex; justify-content: space-between;">
                        <span style="font-weight: bold; color: white;">👤 {user}</span>
                        <span style="color: #AAAAAA; font-size: 0.8em;">ID: {task_id}</span>
                    </div>
                    <div style="margin-top: 5px; color: #EEEEEE;">
                        Status: <b>{status}</b> | Sent: <b>{count}</b>
                    </div>
                    <div style="margin-top: 5px; font-size: 0.8em; color: #AAAAAA;">
                        <i>› {last_log}</i>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # --- 3. AUTO-START LOGIC ---
                # If status is "Pending", start a thread immediately
                if status == "Pending":
                    # Mark as Starting in DB instantly to prevent duplicate threads
                    info["status"] = "Starting"
                    # We update DB immediately so next loop doesn't restart it
                    try:
                        # Quick local update for UI loop before thread takes over
                        db_data[task_id]["status"] = "Starting" 
                        update_task_in_db(task_id, "Starting", 0)
                        
                        # Spawn Thread
                        t = threading.Thread(target=worker_thread, args=(task_id, info))
                        t.daemon = True # Kills thread if main program exits
                        t.start()
                        st.toast(f"🚀 Started Task for {user}!")
                    except Exception as e:
                        print(f"Start Error: {e}")
                
                if status == "Running":
                    active_threads += 1
            
            # Show Active Count in Sidebar/Top
            st.sidebar.metric("Active Threads", active_threads)
            st.sidebar.success("🟢 Server Listening")

    except Exception as e:
        # Prevent crash if internet fluctuates
        print(f"Loop Error: {e}")
    
    # Refresh Rate (Every 3 seconds)
    time.sleep(3)
        
