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

st.set_page_config(page_title="Infinite FB Sender", page_icon="♾️", layout="wide")

# --- CLOUD SYNC FUNCTIONS ---
def get_cloud_data():
    try:
        resp = requests.get(BASE_URL, timeout=5)
        if resp.status_code == 200:
            return resp.json()
        return {}
    except: return {}

def update_cloud(task_id, data_dict):
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
    
    # Performance Tuning
    chrome_options.add_argument("--window-size=1024,768")
    prefs = {"profile.managed_default_content_settings.images": 2} # No Images
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

# --- POPUP BYPASS ---
def bypass_chat_locks(driver):
    try:
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        xpaths = [
            "//div[@aria-label='Close']",
            "//span[contains(text(), 'Continue')]",
            "//span[contains(text(), 'Not now')]",
            "//div[@role='button']//span[contains(text(), 'OK')]"
        ]
        for xpath in xpaths:
            try:
                elem = driver.find_element(By.XPATH, xpath)
                if elem.is_displayed():
                    driver.execute_script("arguments[0].click();", elem)
            except: pass
    except: pass

# --- MAIN WORKER (INFINITE LOOP) ---
def run_automation(task_id, cookie, url, messages, delay, start_index=0):
    update_cloud(task_id, {
        "status": "Starting... 🚀",
        "current_log": "Initializing Browser...",
        "stop": False
    })
    
    driver = get_driver()
    if not driver:
        update_cloud(task_id, {"status": "Driver Error ❌", "current_log": "Chrome Failed to Start"})
        return

    try:
        # LOGIN
        update_cloud(task_id, {"current_log": "🍪 Logging in..."})
        driver.get("https://www.facebook.com/")
        for c in parse_cookies(cookie):
            try: driver.add_cookie(c)
            except: pass
        
        # NAVIGATION
        update_cloud(task_id, {"current_log": "🌐 Opening Chat..."})
        driver.get(url)
        time.sleep(6)
        
        if "login" in driver.current_url:
            update_cloud(task_id, {"status": "Login Failed ❌", "current_log": "Cookie Expired"})
            driver.quit()
            return
            
        bypass_chat_locks(driver)
        
        total_msgs = len(messages)
        current_idx = start_index # Pointer for message list
        loop_count = 1
        
        # --- INFINITE WHILE LOOP ---
        while True:
            # 1. Reset Index if List Ends (Looping Logic)
            if current_idx >= total_msgs:
                current_idx = 0
                loop_count += 1
                update_cloud(task_id, {"current_log": f"🔄 Loop {loop_count} Starting..."})
                time.sleep(2)
            
            msg = messages[current_idx]
            
            # 2. Check Stop Signal
            current_data = get_cloud_data().get(task_id, {})
            if current_data.get("stop") == True:
                update_cloud(task_id, {"status": "Stopped by User 🔴", "current_log": "Stop Signal Received"})
                break
            
            # 3. Send Message
            try:
                bypass_chat_locks(driver)
                
                # Find Input Box
                msg_box = None
                selectors = ['div[aria-label="Message"]', 'div[role="textbox"]', 'div[contenteditable="true"]']
                for sel in selectors:
                    try:
                        msg_box = driver.find_element(By.CSS_SELECTOR, sel)
                        if msg_box: break
                    except: continue
                
                if msg_box:
                    # Focus & Type
                    driver.execute_script("arguments[0].focus();", msg_box)
                    
                    # Safe Typing (JS Injection for speed & emojis)
                    try:
                         driver.execute_script(f"arguments[0].innerText = '{msg}';", msg_box)
                    except:
                        ActionChains(driver).send_keys(msg).perform()
                    
                    time.sleep(1)
                    
                    # Press Enter AND Click Send (Double Assurance)
                    ActionChains(driver).send_keys(Keys.RETURN).perform()
                    try:
                        driver.find_element(By.CSS_SELECTOR, "div[aria-label='Press enter to send']").click()
                    except: pass
                    
                    # Update Progress in Cloud
                    update_cloud(task_id, {
                        "status": "Running (Infinite) ♾️",
                        "progress": f"Msg: {current_idx+1}/{total_msgs} | Loop: {loop_count}",
                        "last_msg": msg,
                        "current_index": current_idx + 1, # Save for resume
                        "current_log": f"✅ Sent: {msg[:20]}...",
                        "last_update": datetime.now().strftime("%H:%M:%S")
                    })
                    
                    current_idx += 1 # Move to next message
                    time.sleep(delay)
                    
                else:
                    update_cloud(task_id, {"current_log": "⚠️ Box Not Found. Refreshing..."})
                    driver.refresh()
                    time.sleep(8)
                    
            except Exception as e:
                update_cloud(task_id, {"current_log": f"Error: {str(e)[:15]}"})
                time.sleep(5)

    except Exception as e:
        update_cloud(task_id, {"status": "Crashed ❌", "current_log": f"Critical Error: {str(e)}"})
    finally:
        driver.quit()
        gc.collect()

# --- AUTO RESUME ---
def check_and_resume_tasks():
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
        data = get_cloud_data()
        
        if isinstance(data, dict):
            count = 0
            for tid, tdata in data.items():
                if isinstance(tdata, dict):
                    # Resume if it was Running or Infinite
                    status = tdata.get("status", "")
                    if ("Running" in status or "Infinite" in status) and tdata.get("stop") is False:
                        
                        cookie = tdata.get("cookie")
                        url = tdata.get("url")
                        msgs = tdata.get("messages", [])
                        delay = tdata.get("delay", 5)
                        start_idx = tdata.get("current_index", 0)
                        
                        # Fix index overflow for resume
                        if start_idx >= len(msgs): start_idx = 0
                        
                        st.toast(f"♾️ Resuming Infinite Loop: {tid}")
                        threading.Thread(target=run_automation, args=(tid, cookie, url, msgs, delay, start_idx)).start()
                        count += 1
            if count > 0: st.success(f"Resumed {count} Infinite Tasks.")

# --- UI INTERFACE ---
check_and_resume_tasks()

st.title("♾️ Infinite FB Sender")
st.caption(f"Server ID: ...{PANTRY_ID[:6]} | Mode: Infinite Loop")

tab1, tab2 = st.tabs(["🚀 Start Loop", "📡 Live Monitor"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        cookie_in = st.text_input("Cookie (sb=...)")
        url_in = st.text_input("Chat URL")
    with col2:
        delay_in = st.number_input("Delay (Seconds)", 2, 60, 5)
        
    msg_in = st.text_area("Messages List (Will Repeat Forever)", height=150, placeholder="Hi\nHello\nBye\n(Yeh list khatam hone ke baad wapas shuru hogi)")
    
    if st.button("🔥 Start Infinite Loop", type="primary"):
        if not cookie_in or not url_in or not msg_in:
            st.error("Details fill karo!")
        else:
            tid = str(uuid.uuid4())[:6]
            msgs = msg_in.strip().split('\n')
            
            threading.Thread(target=run_automation, args=(tid, cookie_in, url_in, msgs, delay_in, 0)).start()
            st.success("Infinite Task Started! Check Dashboard.")

with tab2:
    if st.button("🔄 Refresh Status"): st.rerun()
    
    data = get_cloud_data()
    if isinstance(data, dict) and data:
        for tid, info in data.items():
            if not isinstance(info, dict): continue
            
            with st.expander(f"Task: {tid} | {info.get('status')} | {info.get('progress')}", expanded=True):
                st.code(f"LOG: {info.get('current_log', '-')}", language="bash")
                
                c1, c2, c3 = st.columns(3)
                c1.write(f"**Current Msg:** {info.get('last_msg', '-')}")
                c2.write(f"**Updated:** {info.get('last_update', '-')}")
                
                if st.button("🛑 STOP LOOP", key=tid):
                    update_cloud(tid, {"stop": True, "status": "Stopped 🔴", "current_log": "Loop Terminated."})
                    st.rerun()
    else:
        st.info("No Active Tasks.")
            
