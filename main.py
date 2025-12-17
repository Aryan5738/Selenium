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

# --- 🔐 CONFIGURATION ---
FIXED_BIN_ID = "6942bb0eae596e708fa052f4" 
API_KEY = "$2a$10$6/uFXvi1Lj4R4wsWLipdz.QrNDGyB1RviPCZPFW0DIUmrrNBkLyiu"
BASE_URL = f"https://api.jsonbin.io/v3/b/{FIXED_BIN_ID}"
HEADERS = {"Content-Type": "application/json", "X-Master-Key": API_KEY}

# --- PAGE CONFIG ---
st.set_page_config(page_title="E2EE Master Server", layout="wide", page_icon="⚡")

# --- CSS STYLING (Hacker/Dark Theme) ---
st.markdown("""
<style>
    .stApp { background-color: #0f111a; }
    .task-card {
        background-color: #1a1d29;
        border: 1px solid #2d3342;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 10px;
        border-left: 4px solid #00d4ff;
    }
    .task-card.stopped { border-left: 4px solid #ff4b4b; opacity: 0.7; }
    .status-badge {
        padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;
    }
    .status-running { background-color: #00d4ff; color: black; }
    .status-pending { background-color: #ffd700; color: black; }
    .status-stopped { background-color: #ff4b4b; color: white; }
    .log-text { font-family: monospace; font-size: 12px; color: #a0a0a0; }
</style>
""", unsafe_allow_html=True)

# --- DATABASE HANDLERS ---
def get_db():
    try:
        r = requests.get(BASE_URL + "/latest", headers=HEADERS)
        return r.json()['record'] if r.status_code == 200 else {}
    except: return {}

def update_db_task(task_id, updates):
    """Updates specific fields for a task safely"""
    try:
        current_db = get_db()
        if task_id in current_db:
            current_db[task_id].update(updates)
            # Maintain Last Active timestamp
            current_db[task_id]["last_updated"] = str(datetime.datetime.now())
            requests.put(BASE_URL, headers=HEADERS, json=current_db)
            return True
    except: return False

def force_stop_task(task_id):
    """Admin function to kill a task"""
    return update_db_task(task_id, {"stop_signal": True, "status": "Stopping..."})

# --- SELENIUM WORKER ---
def get_driver():
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    
    bin_path = shutil.which("chromium") or "/usr/bin/chromium"
    driver_path = shutil.which("chromedriver") or "/usr/bin/chromedriver"

    if os.path.exists(bin_path) and os.path.exists(driver_path):
        opts.binary_location = bin_path
        return webdriver.Chrome(service=Service(driver_path), options=opts)
    return None

def worker_thread(task_id, data):
    """The Logic running in background"""
    update_db_task(task_id, {"status": "Initializing", "logs": data.get("logs", []) + ["Allocating Thread..."]})
    
    driver = get_driver()
    if not driver:
        update_db_task(task_id, {"status": "Failed", "logs": ["Driver Error"]})
        return

    try:
        driver.get("https://www.facebook.com/")
        # Cookies
        try:
            for c in data['cookie'].split(';'):
                if '=' in c:
                    n, v = c.strip().split('=', 1)
                    driver.add_cookie({'name': n, 'value': v, 'domain': '.facebook.com'})
        except: pass

        driver.get(data['url'])
        time.sleep(8)
        
        # Popup Killer
        try:
            for btn in driver.find_elements(By.XPATH, "//div[@role='button']//span[contains(text(), 'Continue')]"):
                driver.execute_script("arguments[0].click();", btn)
        except: pass

        count = 0
        update_db_task(task_id, {"status": "Running", "logs": ["Target Locked. Firing..."]})

        while True:
            # Check Stop Signal (From Admin or User)
            if count % 3 == 0:
                fresh = get_db().get(task_id, {})
                if fresh.get("stop_signal", False):
                    update_db_task(task_id, {"status": "Stopped By Admin", "logs": ["🛑 Killed by Admin"]})
                    break

            try:
                # Send Message
                box = driver.find_element(By.CSS_SELECTOR, 'div[aria-label="Message"], div[role="textbox"]')
                driver.execute_script("arguments[0].focus();", box)
                ActionChains(driver).send_keys(data['msg']).send_keys(Keys.RETURN).perform()
                
                count += 1
                
                # Logs update
                log_msg = f"Message #{count} Sent"
                # Fetch fresh logs to append, keeping only last 5
                current_logs = get_db().get(task_id, {}).get("logs", [])
                current_logs.append(log_msg)
                
                update_db_task(task_id, {"count": count, "logs": current_logs[-5:]})
                
                if not data.get('infinite', False):
                    update_db_task(task_id, {"status": "Completed"})
                    break
                else:
                    time.sleep(int(data.get('delay', 2)))
            except:
                time.sleep(5)
                try: # Retry Popups
                    for btn in driver.find_elements(By.XPATH, "//div[@role='button']//span[contains(text(), 'Continue')]"):
                        driver.execute_script("arguments[0].click();", btn)
                except: pass

    except Exception as e:
        update_db_task(task_id, {"status": "Error", "logs": [str(e)]})
    finally:
        driver.quit()

# --- ADMIN PANEL UI ---
st.sidebar.title("🛡️ Admin Login")
if 'admin' not in st.session_state:
    pwd = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        if pwd == "admin123": # PASSWORD
            st.session_state['admin'] = True
            st.rerun()
else:
    st.sidebar.success("Logged In")
    if st.sidebar.button("Logout"):
        del st.session_state['admin']
        st.rerun()

# --- MAIN DASHBOARD ---
st.title("⚡ E2EE Master Control Panel")

if 'admin' in st.session_state:
    st.markdown("### 📡 Live Task Monitor")
    
    # Refresh logic inside a container
    placeholder = st.empty()
    
    # --- AUTO LISTENER LOOP ---
    while True:
        db = get_db()
        
        with placeholder.container():
            # Summary Metrics
            active = len([x for x in db.values() if x.get("status") in ["Running", "Initializing"]])
            total = len(db)
            c1, c2 = st.columns(2)
            c1.metric("Active Threads", active)
            c2.metric("Total Tasks DB", total)
            
            st.divider()
            
            # Sort: Pending > Running > Stopped
            sorted_tasks = sorted(db.items(), key=lambda x: (x[1].get("status")!="Running", x[1].get("status")!="Pending"))

            for tid, data in sorted_tasks:
                status = data.get("status", "Unknown")
                count = data.get("count", 0)
                logs = data.get("logs", [])
                last_log = logs[-1] if logs else "Waiting..."
                
                # Logic to Auto-Start Pending Tasks
                if status == "Pending":
                    # Mark starting immediately locally to prevent dupes in UI loop
                    db[tid]["status"] = "Starting" 
                    update_db_task(tid, {"status": "Starting"})
                    
                    t = threading.Thread(target=worker_thread, args=(tid, data))
                    t.daemon = True
                    t.start()
                    st.toast(f"🚀 Started Task {tid}")

                # UI CARD
                is_stopped = status in ["Stopped", "Completed", "Stopped By Admin", "Error"]
                card_class = "task-card stopped" if is_stopped else "task-card"
                badge_class = "status-stopped" if is_stopped else "status-running"
                
                col_info, col_btn = st.columns([4, 1])
                
                with col_info:
                    st.markdown(f"""
                    <div class="{card_class}">
                        <div style="display:flex; justify-content:space-between;">
                            <span style="color:white; font-weight:bold;">ID: {tid}</span>
                            <span class="status-badge {badge_class}">{status}</span>
                        </div>
                        <div style="margin-top:5px; color:#ddd;">
                            Sent: <b>{count}</b> | Mode: <b>{'Infinite' if data.get('infinite') else 'Single'}</b>
                        </div>
                        <div class="log-text">› {last_log}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col_btn:
                    if not is_stopped:
                        if st.button("⛔ STOP", key=f"btn_{tid}"):
                            force_stop_task(tid)
                            st.toast(f"Stopping {tid}...")

        time.sleep(2) # Refresh Rate
else:
    st.info("Please Login to access the Monitor.")
    # Still run background check? No, server needs admin active tab or UptimeRobot to keep running.
    # To make it run WITHOUT admin login visible, we'd need the loop outside. 
    # But for Admin Control, this is best.
    
