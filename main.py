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

# --- CONFIGURATION ---
# आपकी दी गई BIN ID यहाँ सेट है
FIXED_BIN_ID = "6942bb0eae596e708fa052f4"

st.set_page_config(page_title="Cloud Bridge Bot", layout="centered")
st.title("🤖 FB Bot (Cloud Bridge Mode)")
st.markdown(f"**Linked Bin ID:** `{FIXED_BIN_ID}`")

# --- SELENIUM SETUP ---
def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    
    # Path setup for Streamlit Cloud
    path_chromium = shutil.which("chromium") or "/usr/bin/chromium"
    path_driver = shutil.which("chromedriver") or "/usr/bin/chromedriver"

    if os.path.exists(path_chromium) and os.path.exists(path_driver):
        chrome_options.binary_location = path_chromium
        service = Service(path_driver)
        try:
            return webdriver.Chrome(service=service, options=chrome_options)
        except Exception as e:
            st.error(f"Driver Error: {e}")
            return None
    return None

# --- CLOUD FUNCTIONS ---
def get_cloud_data(api_key):
    url = f"https://api.jsonbin.io/v3/b/{FIXED_BIN_ID}/latest"
    headers = {"X-Master-Key": api_key, "Content-Type": "application/json"}
    try:
        r = requests.get(url, headers=headers)
        return r.json()['record']
    except Exception as e:
        return {"error": str(e)}

def update_cloud_status(api_key, status, count, logs):
    url = f"https://api.jsonbin.io/v3/b/{FIXED_BIN_ID}"
    headers = {"X-Master-Key": api_key, "Content-Type": "application/json"}
    
    try:
        # Fetch current to preserve data
        current = get_cloud_data(api_key)
        if "error" in current: return

        # Update fields
        current["status"] = status
        current["count"] = count
        if "logs" not in current: current["logs"] = []
        
        # Add new logs
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        for log in logs:
            current["logs"].append(f"[{timestamp}] {log}")
        
        # Keep only last 10 logs to save space
        current["logs"] = current["logs"][-10:]
        
        requests.put(url, headers=headers, json=current)
    except:
        pass

# --- WORKER BOT ---
def run_automation(task_data, api_key):
    update_cloud_status(api_key, "Initializing...", 0, ["Starting Chrome Driver..."])
    
    driver = get_driver()
    if not driver:
        update_cloud_status(api_key, "Failed", 0, ["Error: Driver not found"])
        return

    try:
        # 1. Login Logic
        driver.get("https://www.facebook.com/")
        try:
            cookie_str = task_data.get('cookie', '')
            cookies = cookie_str.split(';')
            for c in cookies:
                if '=' in c:
                    n, v = c.strip().split('=', 1)
                    driver.add_cookie({'name': n, 'value': v, 'domain': '.facebook.com'})
        except: 
            pass

        # 2. Open Chat
        driver.get(task_data['url'])
        time.sleep(8)
        
        # 3. Popup Killer
        try:
            btns = driver.find_elements(By.XPATH, "//div[@role='button']//span[contains(text(), 'Continue')]")
            for btn in btns: driver.execute_script("arguments[0].click();", btn)
        except: pass

        count = 0
        keep_running = True
        
        update_cloud_status(api_key, "Running", 0, ["Chat Opened. Starting Loop..."])

        # 4. Message Loop
        while keep_running:
            # Check Stop Signal from Cloud
            latest_data = get_cloud_data(api_key)
            if latest_data.get("stop_signal", False):
                update_cloud_status(api_key, "Stopped", count, ["🛑 Stop Signal Received"])
                break

            try:
                # Find Box & Send
                box = driver.find_element(By.CSS_SELECTOR, 'div[aria-label="Message"], div[role="textbox"]')
                driver.execute_script("arguments[0].focus();", box)
                
                actions = ActionChains(driver)
                actions.send_keys(task_data['msg'])
                actions.send_keys(Keys.RETURN)
                actions.perform()
                
                count += 1
                update_cloud_status(api_key, "Running", count, [f"Sent Msg #{count}"])
                
                if not task_data.get('infinite', False):
                    update_cloud_status(api_key, "Completed", count, ["Single Task Done"])
                    keep_running = False
                else:
                    time.sleep(int(task_data.get('delay', 2)))
                    
            except Exception:
                time.sleep(5)
                # Retry Popup Killer
                try:
                    btns = driver.find_elements(By.XPATH, "//div[@role='button']//span[contains(text(), 'Continue')]")
                    for btn in btns: driver.execute_script("arguments[0].click();", btn)
                except: pass

    except Exception as e:
        update_cloud_status(api_key, "Error", 0, [f"Critical: {str(e)}"])
    finally:
        driver.quit()

# --- MAIN UI LISTENER ---
st.info("ℹ️ Enter your JSONBin API Key to start the server.")

# Password field for API Key
api_key_input = st.text_input("Enter JSONBin API Key (X-Master-Key)", type="password")

if st.button("🔴 Start Listening Server"):
    if not api_key_input:
        st.error("Please enter the API Key first!")
    else:
        st.success("✅ Server is Online & Listening for Termux Commands...")
        st.caption("Do not close this tab. You can minimize it.")
        
        status_placeholder = st.empty()
        log_placeholder = st.empty()
        
        while True:
            # 1. Fetch Cloud Data
            data = get_cloud_data(api_key_input)
            
            if "error" in data:
                status_placeholder.error("Error connecting to Bin. Check API Key.")
                time.sleep(5)
                continue

            status = data.get("status", "Unknown")
            
            # Display Status
            status_placeholder.metric(label="Current Status", value=status, delta=data.get("count", 0))
            
            # Show recent logs
            with log_placeholder.container():
                st.write("Recent Logs:")
                for log in data.get("logs", []):
                    st.code(log)

            # 2. Check if NEW Task is Pending
            if status == "Pending":
                # Change status immediately to prevent double start
                update_cloud_status(api_key_input, "Initializing", 0, ["Command Received. Starting Thread..."])
                
                # Start Thread
                t = threading.Thread(target=run_automation, args=(data, api_key_input))
                t.start()
            
            # 3. Wait before next poll
            time.sleep(3)
    
