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

st.set_page_config(page_title="Pro FB Messenger", page_icon="🛡️", layout="wide")

# --- CLOUD UTILS (FIXED FOR NONE TYPE ERROR) ---
def get_cloud_data():
    try:
        resp = requests.get(BASE_URL, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            # AGAR DATA NULL HAI TO EMPTY DICT RETURN KARO
            if data is None:
                return {}
            return data
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
    options.add_argument("--headless=new") 
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    
    # Anti-Detection
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Performance (No Images)
    prefs = {"profile.managed_default_content_settings.images": 2} 
    options.add_experimental_option("prefs", prefs)
    
    return webdriver.Chrome(options=options)

def parse_cookies(cookie_input):
    if not cookie_input: return [] # Safety Check
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
    # SAFETY: Ensure messages is a list
    if not isinstance(messages, list): 
        messages = []
    
    update_cloud(task_id, {"status": "Starting...", "current_log": "🚀 Initializing...", "stop": False})
    
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
        update_cloud(task_id, {"current_log": f"💬 Opening Chat..."})
        driver.get(url)
        time.sleep(6)
        
        if "login" in driver.current_url:
            update_cloud(task_id, {"status": "Login Failed ❌", "current_log": "Cookie Expired!"})
            driver.quit()
            return
            
        kill_popups(driver)
        
        total_msgs = len(messages)
        if total_msgs == 0:
            update_cloud(task_id, {"status": "Empty List ⚠️", "current_log": "No messages to send."})
            return

        idx = start_index
        loop_num = 1
        
        # 3. INFINITE LOOP
        while True:
            # Check for Empty List or Index Error
            if idx >= total_msgs:
                idx = 0
                loop_num += 1
                update_cloud(task_id, {"current_log": f"🔄 Loop {loop_num} Starting..."})
                time.sleep(3)

            # STOP CHECK
            cdata = get_cloud_data()
            # Safety: Check if cloud data exists
            if isinstance(cdata, dict):
                tdata = cdata.get(task_id, {})
                if isinstance(tdata, dict) and tdata.get("stop") == True:
                    update_cloud(task_id, {"status": "Stopped 🔴", "current_log": "User stopped task."})
                    break

            # SAFETY: Check if messages[idx] exists
            if idx < len(messages):
                msg = messages[idx]
            else:
                msg = "Hi" # Fallback

            try:
                kill_popups(driver)
                
                # FIND BOX
                update_cloud(task_id, {"current_log": "🔍 Finding Box..."})
                msg_box = None
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
                    # TYPE
                    update_cloud(task_id, {"current_log": "✍️ Typing..."})
                    driver.execute_script("arguments[0].focus();", msg_box)
                    try:
                        ActionChains(driver).send_keys(msg).perform()
                    except:
                        driver.execute_script(f"arguments[0].innerText = '{msg}';", msg_box)
                    
                    time.sleep(1)
                    
                    # SEND (Enter + Click)
                    update_cloud(task_id, {"current_log": "🚀 Sending..."})
                    ActionChains(driver).send_keys(Keys.RETURN).perform()
                    try:
                        driver.find_element(By.CSS_SELECTOR, "div[aria-label='Press enter to send']").click()
                    except: pass
                    
                    # SUCCESS
                    update_cloud(task_id, {
                        "status": "Running (Infinite) ♾️",
                        "progress": f"Msg: {idx+1}/{total_msgs} (L:{loop_num})",
                        "last_msg": msg,
                        "current_index": idx + 1,
                        "current_log": f"✅ Sent: {msg[:10]}...",
                        "last_update": datetime.now().strftime("%H:%M:%S")
                    })
                    
                    idx += 1
                    time.sleep(delay)
                    
                else:
                    update_cloud(task_id, {"current_log": "⚠️ Box Not Found! Refreshing..."})
                    driver.refresh()
                    time.sleep(8)

            except Exception as e:
                update_cloud(task_id, {"current_log": f"Error: {str(e)[:20]}"})
                time.sleep(5)

    except Exception as e:
        update_cloud(task_id, {"status": "Crashed ❌", "current_log": f"Critical: {str(e)}"})
    finally:
        driver.quit()
        gc.collect()

# --- AUTO RESUME (SAFE MODE) ---
def auto_resume():
    if 'init' not in st.session_state:
        st.session_state.init = True
        data = get_cloud_data()
        
        # Check if data is valid dict
        if isinstance(data, dict):
            for tid, info in data.items():
                if isinstance(info, dict) and info.get('stop') is False and "Running" in info.get('status', ''):
                    msgs = info.get('messages', [])
                    start = info.get('current_index', 0)
                    if not isinstance(msgs, list): msgs = []
                    
                    st.toast(f"♻️ Resuming: {tid}")
                    threading.Thread(target=run_automation, args=(
                        tid, info.get('cookie'), info.get('url'), msgs, info.get('delay', 5), start
                    )).start()

# --- UI ---
auto_resume()
st.title("🛡️ FB Sender (Crash Proof)")
st.caption(f"Server: Online | ID: {PANTRY_ID[:6]}...")

tab1, tab2 = st.tabs(["🚀 New Task", "📡 Monitor"])

with tab1:
    col1, col2 = st.columns(2)
    cookie_in = col1.text_input("Cookie")
    url_in = col2.text_input("Chat Link")
    
    msg_in = st.text_area("Messages (Infinite Loop)", height=150)
    delay_in = st.slider("Speed (Seconds)", 2, 60, 5)
    
    if st.button("🔥 Start Task", type="primary"):
        if not cookie_in or not url_in or not msg_in:
            st.warning("Fill all details")
        else:
            tid = str(uuid.uuid4())[:6]
            msgs = msg_in.strip().split('\n')
            # Empty line remove karo
            msgs = [m for m in msgs if m.strip()]
            
            if msgs:
                threading.Thread(target=run_automation, args=(tid, cookie_in, url_in, msgs, delay_in)).start()
                st.success("Started!")
            else:
                st.error("Message list empty!")

with tab2:
    if st.button("🔄 Refresh"): st.rerun()
    
    data = get_cloud_data()
    if isinstance(data, dict) and data:
        for tid, info in data.items():
            if not isinstance(info, dict): continue
            
            with st.expander(f"Task {tid} | {info.get('status')}", expanded=True):
                st.info(f"LOG: {info.get('current_log', '-')}")
                c1, c2 = st.columns(2)
                c1.write(f"**Msg:** {info.get('last_msg')}")
                c2.write(f"**Progress:** {info.get('progress')}")
                
                if st.button("🛑 STOP", key=tid):
                    update_cloud(tid, {"stop": True, "status": "Stopped 🔴"})
                    st.rerun()
    else:
        st.write("No tasks running.")
            
