import streamlit as st
import os
import time
import threading
import json
import requests
import gc
import uuid
import random
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

st.set_page_config(page_title="Pro FB Messenger", page_icon="💬", layout="wide")

# --- CLOUD UTILS ---
def get_cloud_data():
    try:
        resp = requests.get(BASE_URL, timeout=5)
        if resp.status_code == 200: return resp.json()
        return {}
    except: return {}

def update_cloud(task_id, data):
    try:
        payload = {task_id: data}
        headers = {'Content-Type': 'application/json'}
        requests.put(BASE_URL, json=payload, headers=headers, timeout=5)
    except: pass

# --- BROWSER ENGINE ---
def get_driver():
    options = Options()
    options.add_argument("--headless=new")  # New headless mode (More stable)
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    
    # Hide Automation Flags (Anti-Detect)
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Mobile User Agent (To force simple chat interface if needed)
    # options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    prefs = {"profile.managed_default_content_settings.images": 2} 
    options.add_experimental_option("prefs", prefs)
    
    return webdriver.Chrome(options=options)

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

# --- POPUP KILLER ---
def kill_popups(driver):
    try:
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        # Common FB Popups
        selectors = [
            "//div[@aria-label='Close']",
            "//span[contains(text(), 'Continue')]",
            "//span[contains(text(), 'Not now')]",
            "//div[@role='button']//span[contains(text(), 'OK')]"
        ]
        for xpath in selectors:
            try:
                btns = driver.find_elements(By.XPATH, xpath)
                for btn in btns:
                    if btn.is_displayed():
                        driver.execute_script("arguments[0].click();", btn)
            except: pass
    except: pass

# --- MAIN AUTOMATION ---
def run_automation(task_id, cookie, url, messages, delay, start_index=0):
    update_cloud(task_id, {"status": "Starting...", "current_log": "🚀 Initializing Chrome...", "stop": False})
    
    driver = get_driver()
    if not driver:
        update_cloud(task_id, {"status": "Error ❌", "current_log": "Driver Failed"})
        return

    try:
        # 1. LOGIN
        update_cloud(task_id, {"current_log": "🍪 Injecting Cookies..."})
        driver.get("https://www.facebook.com/")
        for c in parse_cookies(cookie):
            try: driver.add_cookie(c)
            except: pass
        
        # 2. OPEN CHAT
        update_cloud(task_id, {"current_log": f"💬 Opening Chat: {url[:15]}..."})
        driver.get(url)
        time.sleep(6)
        
        # Check Login
        if "login" in driver.current_url:
            update_cloud(task_id, {"status": "Login Failed ❌", "current_log": "Cookie Expired!"})
            driver.quit()
            return
            
        kill_popups(driver)
        
        total_msgs = len(messages)
        idx = start_index
        loop_num = 1
        
        # 3. INFINITE LOOP
        while True:
            # Loop Restart Logic
            if idx >= total_msgs:
                idx = 0
                loop_num += 1
                update_cloud(task_id, {"current_log": f"🔄 Loop {loop_num} Starting..."})
                time.sleep(3)

            # Check Stop
            cdata = get_cloud_data().get(task_id, {})
            if cdata.get("stop") == True:
                update_cloud(task_id, {"status": "Stopped 🔴", "current_log": "User stopped task."})
                break

            msg = messages[idx]

            try:
                kill_popups(driver)
                
                # --- FIND INPUT BOX (Robust Method) ---
                update_cloud(task_id, {"current_log": "🔍 Finding Input Box..."})
                
                msg_box = None
                # New FB uses 'lexical-editor', Old uses 'textbox'
                css_selectors = [
                    'div[aria-label="Message"]',
                    'div[role="textbox"]',
                    'div[data-lexical-editor="true"]',
                    'div[contenteditable="true"]'
                ]
                
                for css in css_selectors:
                    try:
                        element = driver.find_element(By.CSS_SELECTOR, css)
                        if element.is_displayed():
                            msg_box = element
                            break
                    except: continue
                
                if msg_box:
                    # Type Message
                    update_cloud(task_id, {"current_log": "✍️ Typing Message..."})
                    driver.execute_script("arguments[0].focus();", msg_box)
                    
                    # Safe Typing
                    try:
                        ActionChains(driver).send_keys(msg).perform()
                    except:
                        driver.execute_script(f"arguments[0].innerText = '{msg}';", msg_box)
                    
                    time.sleep(1)
                    
                    # --- SENDING LOGIC (The Fix) ---
                    update_cloud(task_id, {"current_log": "🚀 Sending..."})
                    
                    # Method 1: Enter Key
                    ActionChains(driver).send_keys(Keys.RETURN).perform()
                    time.sleep(0.5)
                    
                    # Method 2: Click Send Icon (If Enter failed)
                    try:
                        # FB Send Icon usually has this label
                        send_btn = driver.find_element(By.CSS_SELECTOR, "div[aria-label='Press enter to send']")
                        send_btn.click()
                    except:
                        pass # Arrow icon not found, maybe Enter worked
                    
                    # Update Success
                    update_cloud(task_id, {
                        "status": "Running (Infinite) ♾️",
                        "progress": f"Msg: {idx+1}/{total_msgs} (L:{loop_num})",
                        "last_msg": msg,
                        "current_index": idx + 1,
                        "current_log": f"✅ Sent: {msg[:15]}...",
                        "last_update": datetime.now().strftime("%H:%M:%S")
                    })
                    
                    idx += 1
                    time.sleep(delay)
                    
                else:
                    update_cloud(task_id, {"current_log": "⚠️ Input Box Not Found! Refreshing..."})
                    driver.refresh()
                    time.sleep(8)

            except Exception as e:
                update_cloud(task_id, {"current_log": f"Error: {str(e)[:20]}"})
                time.sleep(5)
                # Recover
                kill_popups(driver)

    except Exception as e:
        update_cloud(task_id, {"status": "Crashed ❌", "current_log": f"Critical: {str(e)}"})
    finally:
        driver.quit()
        gc.collect()

# --- AUTO RESUME ---
def auto_resume():
    if 'init' not in st.session_state:
        st.session_state.init = True
        data = get_cloud_data()
        if isinstance(data, dict):
            for tid, info in data.items():
                if isinstance(info, dict) and info.get('stop') is False and "Running" in info.get('status', ''):
                    # Resume
                    msgs = info.get('messages', [])
                    start = info.get('current_index', 0)
                    if start >= len(msgs): start = 0
                    
                    st.toast(f"♻️ Resuming Task: {tid}")
                    threading.Thread(target=run_automation, args=(
                        tid, info.get('cookie'), info.get('url'), msgs, info.get('delay', 5), start
                    )).start()

# --- UI ---
auto_resume()
st.title("♾️ FB Messenger Pro (Live)")
st.caption(f"Server: {PANTRY_ID[:8]}... | Status: Online")

tab1, tab2 = st.tabs(["🚀 New Task", "📡 Live Monitor"])

with tab1:
    col1, col2 = st.columns(2)
    cookie_in = col1.text_input("Cookie (sb=...)")
    url_in = col2.text_input("Chat Link")
    
    msg_in = st.text_area("Messages List (Infinite Loop)", height=150, placeholder="Hello\nTesting\nBye")
    delay_in = st.slider("Speed (Seconds)", 2, 60, 5)
    
    if st.button("🔥 Start Infinite Message", type="primary"):
        if not cookie_in or not url_in or not msg_in:
            st.warning("Please fill all fields")
        else:
            tid = str(uuid.uuid4())[:6]
            msgs = msg_in.strip().split('\n')
            threading.Thread(target=run_automation, args=(tid, cookie_in, url_in, msgs, delay_in)).start()
            st.success("Task Started! Check Monitor Tab.")

with tab2:
    if st.button("🔄 Refresh Logs"): st.rerun()
    
    data = get_cloud_data()
    if isinstance(data, dict) and data:
        for tid, info in data.items():
            if not isinstance(info, dict): continue
            
            with st.expander(f"Task {tid} | {info.get('status')}", expanded=True):
                # REAL TIME LOGS
                st.info(f"📋 LOG: {info.get('current_log', 'Waiting...')}")
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Progress", info.get('progress'))
                c2.write(f"**Msg:** {info.get('last_msg')}")
                c3.write(f"**Time:** {info.get('last_update')}")
                
                if st.button("🛑 STOP", key=tid):
                    update_cloud(tid, {"stop": True, "status": "Stopped 🔴", "current_log": "Terminated"})
                    st.rerun()
    else:
        st.write("No active tasks.")
                           
