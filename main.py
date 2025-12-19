import streamlit as st
import os
import time
import threading
import json
import requests
import gc # Garbage Collector for RAM cleanup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

# --- SYSTEM CONFIGURATION ---
MAX_CONCURRENT_TASKS = 2  # Sirf 2 Browser ek sath chalenge (RAM bachane ke liye)
task_semaphore = threading.Semaphore(MAX_CONCURRENT_TASKS)

# --- PANTRY CONFIG ---
try:
    with open('config.json', 'r') as f:
        config = json.load(f)
    PANTRY_ID = config['pantry_id']
    CMD_BASKET = config['baskets']['command_queue']
    STATUS_BASKET = config['baskets']['status_log']
    BASE_URL = f"{config['base_url']}/{PANTRY_ID}/basket"
except:
    PANTRY_ID = "ccdeb288-5806-4b0b-ad98-899782e7a901"
    CMD_BASKET = "command_queue"
    STATUS_BASKET = "newBasket59"
    BASE_URL = f"https://getpantry.cloud/apiv1/pantry/{PANTRY_ID}/basket"

st.set_page_config(page_title="Ultra-Lite Server", layout="wide", page_icon="⚡")

# --- UTILS ---
def get_basket(basket_name):
    try:
        resp = requests.get(f"{BASE_URL}/{basket_name}", timeout=10)
        if resp.status_code == 200:
            return resp.json()
        return {}
    except:
        return {}

def update_status(task_id, status_data):
    try:
        payload = {task_id: status_data}
        headers = {'Content-Type': 'application/json'}
        requests.put(f"{BASE_URL}/{STATUS_BASKET}", json=payload, headers=headers, timeout=10)
    except: pass

# --- OPTIMIZED DRIVER SETUP ---
def get_driver():
    chrome_options = Options()
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    chrome_options.add_argument(f'user-agent={user_agent}')
    
    # --- RAM & CPU SAVING FLAGS (VERY IMPORTANT) ---
    chrome_options.add_argument("--headless=new") # New headless mode is more stable
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-notifications")
    
    # Block Images (Saves 70% RAM/Bandwidth)
    prefs = {"profile.managed_default_content_settings.images": 2}
    chrome_options.add_experimental_option("prefs", prefs)
    
    # Page Load Strategy (Don't wait for full page load)
    chrome_options.page_load_strategy = 'eager'
    
    # Small Window Size (Less Rendering = Less RAM)
    chrome_options.add_argument("--window-size=800,600")
    
    try:
        return webdriver.Chrome(options=chrome_options)
    except Exception as e:
        print(f"Driver Init Error: {e}")
        return None

def parse_cookies(cookie_input):
    # (Cookie parsing logic same as before)
    cookies = []
    try:
        if isinstance(cookie_input, list): return cookie_input
        if cookie_input.strip().startswith('['): return json.loads(cookie_input)
        lines = cookie_input.split('\n')
        for line in lines:
            parts = line.split('\t')
            if len(parts) >= 7:
                cookies.append({'name': parts[5], 'value': parts[6].strip(), 'domain': parts[0]})
        if not cookies:
            items = cookie_input.split(';')
            for item in items:
                if '=' in item:
                    name, value = item.strip().split('=', 1)
                    cookies.append({'name': name, 'value': value, 'domain': '.facebook.com'})
        return cookies
    except: return []

# --- MAIN TASK LOGIC ---
def run_automation(task_id, task_data):
    # 1. ACQUIRE LOCK (Queue System)
    # Agar 2 browser pehle se chal rahe hain, to ye yahan wait karega
    update_status(task_id, {"status": "In Queue (Waiting)... ⏳", "stop": False})
    
    with task_semaphore: 
        # Ab baari aayi hai
        url = task_data.get('url')
        msg = task_data.get('msg')
        cookie = task_data.get('cookie')
        delay = int(task_data.get('delay', 10))

        update_status(task_id, {"status": "Starting Lite Driver... 🚀", "stop": False})
        
        driver = get_driver()
        if not driver:
            update_status(task_id, {"status": "Driver Failed (RAM Full?) ❌", "stop": True})
            return

        try:
            driver.get("https://www.facebook.com/")
            cookies = parse_cookies(cookie)
            for c in cookies:
                try: driver.add_cookie(c)
                except: pass
            
            driver.get(url)
            time.sleep(5)
            
            # Anti-Popup
            try: ActionChains(driver).send_keys(Keys.ESCAPE).perform()
            except: pass
            
            sent_count = 0
            update_status(task_id, {"status": "Running (Low CPU Mode) 🟢", "sent": 0})

            while True:
                # Check Stop Signal
                try:
                    live_data = get_basket(STATUS_BASKET)
                    task_info = live_data.get(task_id, {})
                    if task_info.get("stop") == True or "STOP" in task_info.get("status", ""):
                        update_status(task_id, {"status": "Stopped by User 🔴", "stop": True, "sent": sent_count})
                        break
                except: pass

                # Send Message
                try:
                    msg_box = driver.find_element(By.CSS_SELECTOR, 'div[aria-label="Message"], div[role="textbox"]')
                    driver.execute_script("arguments[0].focus();", msg_box)
                    ActionChains(driver).send_keys(msg).send_keys(Keys.RETURN).perform()
                    
                    sent_count += 1
                    
                    # Double Check Stop
                    live_data_now = get_basket(STATUS_BASKET)
                    if live_data_now.get(task_id, {}).get("stop") == True: break

                    update_status(task_id, {
                        "status": "Running 🟢", 
                        "sent": sent_count,
                        "stop": False,
                        "last_update": time.strftime("%H:%M:%S")
                    })
                    
                    time.sleep(delay)
                    
                except Exception:
                    time.sleep(5)
                    try: ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                    except: pass

        except Exception as e:
            update_status(task_id, {"status": f"Error: {str(e)}", "sent": sent_count})
        finally:
            # CLEANUP (Very Important for preventing crashes)
            if driver:
                driver.quit()
            
            # Update Final Status
            update_status(task_id, {"status": "Stopped 🔴", "sent": sent_count, "stop": True})
            
            # FORCE MEMORY CLEANUP
            del driver
            gc.collect() 

def process_queue():
    if 'processed_tasks' not in st.session_state:
        st.session_state.processed_tasks = set()

    commands = get_basket(CMD_BASKET)
    statuses = get_basket(STATUS_BASKET)

    if commands and isinstance(commands, dict):
        for task_id, data in commands.items():
            if task_id == "info": continue
            
            # Check if already processed
            if task_id not in st.session_state.processed_tasks:
                
                # Check if already running in cloud
                current_status = statuses.get(task_id, {}).get('status', '')
                if "Running" in current_status or "Queue" in current_status:
                    st.session_state.processed_tasks.add(task_id)
                    continue

                st.toast(f"📥 New Task Received: {task_id}")
                st.session_state.processed_tasks.add(task_id)
                
                # Start Thread (Background)
                t = threading.Thread(target=run_automation, args=(task_id, data))
                t.daemon = True
                t.start()

# --- UI ---
st.title("⚡ Ultra-Lite FB Server")
st.markdown("### `Low Resource Mode Enabled (20% CPU Limit)`")
st.caption(f"Max Concurrent Browsers: {MAX_CONCURRENT_TASKS}")

col1, col2 = st.columns(2)
with col1:
    if st.button("🧹 Clear Memory (GC)"):
        gc.collect()
        st.toast("RAM Cleared!")
with col2:
    if st.button("🔄 Check Queue"):
        st.session_state.processed_tasks = set()
        process_queue()

# Live Monitor
placeholder = st.empty()

while True:
    process_queue()
    
    statuses = get_basket(STATUS_BASKET)
    clean_status = {k: v for k, v in statuses.items() if k != "info"}
    
    with placeholder.container():
        if clean_status:
            # Custom styled table for better view
            st.dataframe(
                clean_status, 
                column_config={
                    "status": "Current Status",
                    "sent": "Msgs Sent",
                    "last_update": "Last Active"
                },
                use_container_width=True
            )
        else:
            st.info("System Idle. Waiting for tasks...")
    
    time.sleep(5)
            
