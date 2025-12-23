import streamlit as st
import os
import time
import threading
import json
import requests
import gc
import uuid
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

# --- CONFIGURATION ---
PANTRY_ID = "ccdeb288-5806-4b0b-ad98-899782e7a901"
BASKET_NAME = "savedata"
BASE_URL = f"https://getpantry.cloud/apiv1/pantry/{PANTRY_ID}/basket/{BASKET_NAME}"

st.set_page_config(page_title="Pro FB Sender", page_icon="⚡", layout="wide")

# --- CLOUD SYNC FUNCTIONS ---
def get_cloud_data():
    try:
        resp = requests.get(BASE_URL, timeout=5)
        if resp.status_code == 200:
            return resp.json()
        return {}
    except: return {}

def update_cloud(task_id, data_dict):
    """Updates specific fields in the cloud"""
    try:
        payload = {task_id: data_dict}
        headers = {'Content-Type': 'application/json'}
        requests.put(BASE_URL, json=payload, headers=headers, timeout=5)
    except Exception as e:
        print(f"Cloud Update Error: {e}")

# --- BROWSER SETUP ---
def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-notifications")
    
    # 20% CPU Use Limit & Fast Load
    chrome_options.add_argument("--window-size=1024,768")
    prefs = {"profile.managed_default_content_settings.images": 2} # Block Images
    chrome_options.add_experimental_option("prefs", prefs)
    
    return webdriver.Chrome(options=chrome_options)

def parse_cookies(cookie_input):
    cookies = []
    try:
        if isinstance(cookie_input, list): return cookie_input
        if cookie_input.strip().startswith('['): return json.loads(cookie_input)
        items = cookie_input.split(';')
        for item in items:
            if '=' in item:
                name, value = item.strip().split('=', 1)
                cookies.append({'name': name, 'value': value, 'domain': '.facebook.com'})
        return cookies
    except: return []

# --- POPUP & LOCK BYPASS ---
def bypass_chat_locks(driver):
    try:
        # 1. Press Escape
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        
        # 2. Click Common Popups
        xpaths = [
            "//div[@aria-label='Close']",
            "//span[contains(text(), 'Continue')]",
            "//span[contains(text(), 'Not now')]",
            "//div[@role='button']//span[contains(text(), 'OK')]",
            "//div[@aria-label='OK']"
        ]
        for xpath in xpaths:
            try:
                elem = driver.find_element(By.XPATH, xpath)
                if elem.is_displayed():
                    driver.execute_script("arguments[0].click();", elem)
            except: pass
    except: pass

# --- MAIN WORKER ---
def run_automation(task_id, cookie, url, messages, delay, start_index=0):
    # Initial Log
    update_cloud(task_id, {
        "status": "Initializing...",
        "current_log": "🚀 Starting Browser...",
        "stop": False
    })
    
    driver = get_driver()
    if not driver:
        update_cloud(task_id, {"status": "Driver Error ❌", "current_log": "Failed to open Chrome"})
        return

    try:
        # 1. LOGIN
        update_cloud(task_id, {"current_log": "🍪 Injecting Cookies..."})
        driver.get("https://www.facebook.com/")
        for c in parse_cookies(cookie):
            try: driver.add_cookie(c)
            except: pass
        
        # 2. NAVIGATION
        update_cloud(task_id, {"current_log": f"🌐 Navigating to Chat: {url[:15]}..."})
        driver.get(url)
        time.sleep(5)
        
        # Check if loaded
        if "login" in driver.current_url:
            update_cloud(task_id, {"status": "Login Failed ❌", "current_log": "Cookie Expired or Invalid"})
            driver.quit()
            return
            
        bypass_chat_locks(driver)
        
        total_msgs = len(messages)
        
        # 3. MESSAGE LOOP
        for i in range(start_index, total_msgs):
            msg = messages[i]
            
            # Stop Check
            current_data = get_cloud_data().get(task_id, {})
            if current_data.get("stop") == True or "Finished" in current_data.get("status", ""):
                break
            
            # --- SENDING LOGIC ---
            try:
                update_cloud(task_id, {"current_log": f"🔍 Finding Message Box for Msg #{i+1}..."})
                bypass_chat_locks(driver)
                
                # Attempt 1: Find Box
                msg_box = None
                selectors = [
                    'div[aria-label="Message"]', 
                    'div[role="textbox"]', 
                    'div[contenteditable="true"]',
                    'div[data-lexical-editor="true"]'
                ]
                
                for sel in selectors:
                    try:
                        msg_box = driver.find_element(By.CSS_SELECTOR, sel)
                        if msg_box: break
                    except: continue
                
                if msg_box:
                    # Type Message
                    update_cloud(task_id, {"current_log": "✍️ Typing Message..."})
                    driver.execute_script("arguments[0].focus();", msg_box)
                    
                    # Method A: Send Keys
                    try: 
                        ActionChains(driver).send_keys(msg).perform()
                    except:
                         # Method B: JS Injection (For emojis/symbols)
                        driver.execute_script(f"arguments[0].innerText = '{msg}';", msg_box)

                    time.sleep(1)
                    
                    # CLICK SEND BUTTON (Fix for Stuck Issue)
                    update_cloud(task_id, {"current_log": "🚀 Clicking Send Button..."})
                    
                    sent = False
                    # Try Enter Key
                    ActionChains(driver).send_keys(Keys.RETURN).perform()
                    time.sleep(1)
                    
                    # Try Finding Send Icon (SVG) and Click
                    try:
                        send_btn = driver.find_element(By.CSS_SELECTOR, "div[aria-label='Press enter to send']")
                        send_btn.click()
                        sent = True
                    except: 
                        # Enter usually works if button not found
                        pass
                    
                    # --- SUCCESS UPDATE ---
                    update_cloud(task_id, {
                        "status": "Running 🟢",
                        "progress": f"{i+1}/{total_msgs}",
                        "last_msg": msg,
                        "current_index": i + 1,
                        "current_log": f"✅ Message {i+1} Sent!",
                        "last_update": datetime.now().strftime("%H:%M:%S")
                    })
                    
                    time.sleep(delay)
                else:
                    update_cloud(task_id, {"current_log": "⚠️ Box Not Found! Retrying..."})
                    time.sleep(5)
                    driver.refresh() # Page reload try
                    time.sleep(5)

            except Exception as e:
                update_cloud(task_id, {"current_log": f"⚠️ Error: {str(e)[:20]}"})
                time.sleep(5)

        # Finish
        update_cloud(task_id, {"status": "Finished ✅", "stop": True, "current_log": "All Messages Sent."})

    except Exception as e:
        update_cloud(task_id, {"status": "Crashed ❌", "current_log": f"Critical: {str(e)}"})
    finally:
        driver.quit()
        gc.collect()

# --- AUTO RESUME ---
def check_and_resume_tasks():
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
        data = get_cloud_data()
        
        if not isinstance(data, dict): return
        
        count = 0
        for tid, tdata in data.items():
            if not isinstance(tdata, dict): continue
            
            if tdata.get("status") == "Running 🟢" and tdata.get("stop") is False:
                cookie = tdata.get("cookie")
                url = tdata.get("url")
                msgs = tdata.get("messages", [])
                delay = tdata.get("delay", 5)
                start_idx = tdata.get("current_index", 0)
                
                if start_idx < len(msgs):
                    st.toast(f"🔄 Resuming {tid}...")
                    threading.Thread(target=run_automation, args=(tid, cookie, url, msgs, delay, start_idx)).start()
                    count += 1
        if count > 0: st.success(f"Resumed {count} tasks.")

# --- UI INTERFACE ---
check_and_resume_tasks()

st.title("⚡ Real-Time FB Sender")
st.caption(f"Server ID: {PANTRY_ID[:8]}...")

tab1, tab2 = st.tabs(["🚀 New Task", "📡 Live Dashboard"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        cookie_in = st.text_input("Cookie", placeholder="sb=...")
        url_in = st.text_input("Chat URL", placeholder="https://www.facebook.com/messages/t/...")
    with col2:
        delay_in = st.number_input("Delay (Seconds)", 2, 60, 5)
        
    msg_in = st.text_area("Messages", height=150, placeholder="Message 1\nMessage 2\n(Line by line)")
    
    if st.button("🔥 Start Task", type="primary"):
        if not cookie_in or not url_in or not msg_in:
            st.error("Fill all details!")
        else:
            tid = str(uuid.uuid4())[:6]
            msgs = msg_in.strip().split('\n')
            
            threading.Thread(target=run_automation, args=(tid, cookie_in, url_in, msgs, delay_in, 0)).start()
            st.success("Started! Check Dashboard tab.")

with tab2:
    if st.button("🔄 Refresh Logs"): st.rerun()
    
    data = get_cloud_data()
    if isinstance(data, dict) and data:
        for tid, info in data.items():
            if not isinstance(info, dict): continue
            
            # --- CARD UI FOR EACH TASK ---
            with st.expander(f"Task: {tid} | {info.get('status')} | {info.get('progress')}", expanded=True):
                
                # Real-Time Log Display
                log_text = info.get('current_log', 'Waiting...')
                st.code(f"LOG: {log_text}", language="bash")
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Progress", info.get('progress', '0/0'))
                c2.write(f"**Last Msg:** {info.get('last_msg', '-')}")
                c3.write(f"**Updated:** {info.get('last_update', '-')}")
                
                if st.button("🛑 Stop", key=tid):
                    update_cloud(tid, {"stop": True, "status": "Stopped 🔴", "current_log": "User stopped task."})
                    st.rerun()
    else:
        st.info("No Active Tasks.")
    
