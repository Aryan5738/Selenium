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

st.set_page_config(page_title="Ultimate FB Sender", page_icon="🤖", layout="wide")

# --- CLOUD SYNC FUNCTIONS ---
def get_cloud_data():
    """Pantry se sara data fetch karta hai"""
    try:
        resp = requests.get(BASE_URL)
        if resp.status_code == 200:
            return resp.json()
        return {}
    except: return {}

def update_task_in_cloud(task_id, data):
    """Specific task ko cloud me update karta hai"""
    try:
        payload = {task_id: data}
        headers = {'Content-Type': 'application/json'}
        # PUT request data ko merge karta hai
        requests.put(BASE_URL, json=payload, headers=headers)
    except Exception as e:
        print(f"Cloud Error: {e}")

# --- BROWSER SETUP ---
def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-notifications")
    
    # Image loading band (Fast Speed & Low RAM)
    prefs = {"profile.managed_default_content_settings.images": 2}
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

# --- POPUP KILLER ---
def bypass_chat_locks(driver):
    try:
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        xpaths = [
            "//div[@aria-label='Close']",
            "//span[contains(text(), 'Continue')]",
            "//span[contains(text(), 'Not now')]",
            "//span[contains(text(), 'Restore')]",
            "//div[@role='button']//span[contains(text(), 'OK')]"
        ]
        for xpath in xpaths:
            try:
                btns = driver.find_elements(By.XPATH, xpath)
                for btn in btns:
                    if btn.is_displayed():
                        driver.execute_script("arguments[0].click();", btn)
            except: pass
    except: pass

# --- MAIN WORKER ---
def run_automation(task_id, cookie, url, messages, delay, start_index=0):
    update_task_in_cloud(task_id, {
        "status": "Starting Driver... ⚙️", 
        "progress": f"{start_index}/{len(messages)}",
        "cookie": cookie, "url": url, "messages": messages, "delay": delay,
        "current_index": start_index,
        "stop": False
    })
    
    driver = get_driver()
    if not driver:
        update_task_in_cloud(task_id, {"status": "Driver Error ❌"})
        return

    try:
        driver.get("https://www.facebook.com/")
        for c in parse_cookies(cookie):
            try: driver.add_cookie(c)
            except: pass
        
        driver.get(url)
        time.sleep(8)
        bypass_chat_locks(driver)
        
        total_msgs = len(messages)
        
        for i in range(start_index, total_msgs):
            msg = messages[i]
            
            # Check Stop Signal
            current_cloud = get_cloud_data()
            # Safety check
            if isinstance(current_cloud, dict):
                task_data = current_cloud.get(task_id, {})
                if isinstance(task_data, dict):
                    if task_data.get("stop") == True or "Finished" in task_data.get("status", ""):
                        print(f"Stopping Task {task_id}")
                        break

            try:
                bypass_chat_locks(driver)
                
                msg_box = None
                selectors = ['div[aria-label="Message"]', 'div[role="textbox"]', 'div[contenteditable="true"]']
                for sel in selectors:
                    try:
                        msg_box = driver.find_element(By.CSS_SELECTOR, sel)
                        break
                    except: continue
                
                if msg_box:
                    driver.execute_script("arguments[0].focus();", msg_box)
                    ActionChains(driver).send_keys(msg).send_keys(Keys.RETURN).perform()
                    
                    # SAVE PROGRESS (Persistence)
                    update_task_in_cloud(task_id, {
                        "status": "Running 🟢",
                        "progress": f"{i+1}/{total_msgs}",
                        "last_msg": msg,
                        "current_index": i + 1, # Next start point
                        "last_update": datetime.now().strftime("%H:%M:%S")
                    })
                    
                    time.sleep(delay)
                else:
                    time.sleep(5)
            except Exception as e:
                time.sleep(5)

        update_task_in_cloud(task_id, {"status": "Completed ✅", "progress": "Done", "stop": True})

    except Exception as e:
        update_task_in_cloud(task_id, {"status": f"Crashed: {str(e)[:20]} ⚠️"})
    finally:
        driver.quit()
        gc.collect()

# --- AUTO RESUME LOGIC (FIXED) ---
def check_and_resume_tasks():
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
        
        cloud_data = get_cloud_data()
        
        # 1. Pehla Security Check
        if not isinstance(cloud_data, dict):
            return

        count = 0
        for tid, data in cloud_data.items():
            # 2. Dusra Security Check (Jo error de raha tha)
            if not isinstance(data, dict):
                continue
            
            # Ab safe hai .get() use karna
            if data.get("status") == "Running 🟢" and data.get("stop") is False:
                
                cookie = data.get("cookie")
                url = data.get("url")
                msgs = data.get("messages", [])
                delay = data.get("delay", 5)
                start_idx = data.get("current_index", 0)
                
                if start_idx < len(msgs):
                    st.toast(f"🔄 Resuming Task: {tid} from line {start_idx}")
                    t = threading.Thread(
                        target=run_automation, 
                        args=(tid, cookie, url, msgs, delay, start_idx)
                    )
                    t.start()
                    count += 1
        
        if count > 0:
            st.success(f"Successfully Resumed {count} Tasks from Cloud!")

# --- UI INTERFACE ---
check_and_resume_tasks()

st.title("☁️ Auto-Resumable FB Sender")
st.caption(f"Storage: {BASKET_NAME}")

tab1, tab2 = st.tabs(["🚀 New Task", "📡 Live Dashboard"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        cookie_in = st.text_input("Paste Cookie")
        url_in = st.text_input("Chat URL")
    with col2:
        delay_in = st.number_input("Delay (Seconds)", 2, 300, 5)
        
    msg_in = st.text_area("Messages (Line by Line)", height=150, placeholder="Hi\nHello\nKaise ho")
    
    if st.button("🔥 Launch Task", type="primary"):
        if not cookie_in or not url_in or not msg_in:
            st.error("All fields required!")
        else:
            task_id = str(uuid.uuid4())[:6]
            messages_list = msg_in.strip().split('\n')
            
            st.info(f"Task {task_id} initialized.")
            
            t = threading.Thread(
                target=run_automation,
                args=(task_id, cookie_in, url_in, messages_list, delay_in, 0)
            )
            t.start()
            st.success("Task Started! Check Dashboard.")

with tab2:
    if st.button("🔄 Refresh Cloud Data"):
        st.rerun()
        
    data = get_cloud_data()
    
    if isinstance(data, dict) and data:
        for tid, info in data.items():
            if not isinstance(info, dict): continue
            
            with st.expander(f"Task: {tid} | {info.get('status', 'Unknown')}", expanded=True):
                c1, c2, c3 = st.columns(3)
                c1.write(f"**Progress:** {info.get('progress', '0/0')}")
                c2.write(f"**Last Msg:** {info.get('last_msg', '-')}")
                c3.write(f"**Update:** {info.get('last_update', '-')}")
                
                if st.button("🛑 Stop / Delete", key=tid):
                    update_task_in_cloud(tid, {"stop": True, "status": "Stopped by User 🔴"})
                    st.rerun()
    else:
        st.info("Cloud Basket is Empty.")
        
