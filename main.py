import streamlit as st
import os
import time
import threading
import json
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

# --- CONFIGURATION ---
PANTRY_ID = "ccdeb288-5806-4b0b-ad98-899782e7a901"
CMD_BASKET = "command_queue"  # Yahan naye task aayenge
STATUS_BASKET = "newBasket59" # Yahan status save hoga

BASE_URL = f"https://getpantry.cloud/apiv1/pantry/{PANTRY_ID}/basket"

st.set_page_config(page_title="FB Multi-Bot Server", layout="wide")

# --- PANTRY HELPER FUNCTIONS ---
def get_basket(basket_name):
    try:
        resp = requests.get(f"{BASE_URL}/{basket_name}")
        if resp.status_code == 200:
            return resp.json()
        return {}
    except:
        return {}

def update_status(task_id, status_data):
    """Updates status inside the Status Basket"""
    try:
        # Hum pura basket replace nahi karenge, sirf specific key update karenge (Safe Put)
        # Pantry API allows updating specific keys by sending just that JSON
        payload = {task_id: status_data}
        headers = {'Content-Type': 'application/json'}
        requests.put(f"{BASE_URL}/{STATUS_BASKET}", json=payload, headers=headers)
    except Exception as e:
        print(f"Status Update Error: {e}")

def delete_command(task_id):
    """Commands ko process hone ke baad queue se hata dena chahiye"""
    # Pantry delete key API nahi deta seedha, toh hume basket read karke, key hata kar wapis post karna padega
    # (Simplified: Hum server memory me track kar lenge ki ye process ho gaya)
    pass 

# --- SELENIUM BOT ---
def get_driver():
    chrome_options = Options()
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    chrome_options.add_argument(f'user-agent={user_agent}')
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    
    # Streamlit Cloud Paths
    return webdriver.Chrome(options=chrome_options)

def parse_cookies(cookie_string):
    cookies = []
    try:
        if cookie_string.strip().startswith('['):
            return json.loads(cookie_string)
        lines = cookie_string.split('\n')
        for line in lines:
            parts = line.split('\t')
            if len(parts) >= 7:
                cookies.append({'name': parts[5], 'value': parts[6].strip(), 'domain': parts[0]})
        if not cookies:
            items = cookie_string.split(';')
            for item in items:
                if '=' in item:
                    name, value = item.strip().split('=', 1)
                    cookies.append({'name': name, 'value': value, 'domain': '.facebook.com'})
        return cookies
    except:
        return []

def run_automation(task_id, task_data):
    url = task_data.get('url')
    msg = task_data.get('msg')
    cookie = task_data.get('cookie')
    delay = int(task_data.get('delay', 10))

    update_status(task_id, {"status": "Starting Driver...", "sent": 0})
    
    driver = get_driver()
    if not driver:
        update_status(task_id, {"status": "Driver Failed", "sent": 0})
        return

    try:
        driver.get("https://www.facebook.com/")
        cookies = parse_cookies(cookie)
        for c in cookies:
            try: driver.add_cookie(c)
            except: pass
        
        driver.get(url)
        time.sleep(8)
        
        # Popup Bypass
        try: ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        except: pass
        
        sent_count = 0
        update_status(task_id, {"status": "Running", "sent": 0})

        while True:
            # Check Stop Signal from Pantry (Optional implementation)
            # send message
            try:
                msg_box = driver.find_element(By.CSS_SELECTOR, 'div[aria-label="Message"], div[role="textbox"]')
                driver.execute_script("arguments[0].focus();", msg_box)
                ActionChains(driver).send_keys(msg).send_keys(Keys.RETURN).perform()
                sent_count += 1
                
                update_status(task_id, {
                    "status": "Running", 
                    "sent": sent_count,
                    "last_update": time.strftime("%H:%M:%S")
                })
                
                time.sleep(delay)
            except:
                time.sleep(5)
                try: ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                except: pass

    except Exception as e:
        update_status(task_id, {"status": f"Error: {str(e)}", "sent": sent_count})
    finally:
        driver.quit()
        update_status(task_id, {"status": "Stopped", "sent": sent_count})

# --- BACKGROUND MONITOR ---
def process_queue():
    """Checks Pantry for new commands"""
    if 'processed_tasks' not in st.session_state:
        st.session_state.processed_tasks = set()

    commands = get_basket(CMD_BASKET)
    
    for task_id, data in commands.items():
        if task_id not in st.session_state.processed_tasks:
            # New Task Found!
            st.toast(f"New Task Received: {task_id}")
            st.session_state.processed_tasks.add(task_id)
            
            # Start Thread
            t = threading.Thread(target=run_automation, args=(task_id, data))
            t.start()
            
            # Remove from command queue (Optional cleanup)
            # Yahan hum basket clear nahi kar rahe taaki complexity na badhe
            # Real production me hume command queue clean karni chahiye

# --- UI LAYOUT ---
st.title("🤖 FB Multi-User Server (Streamlit)")
st.write("Listening for commands from Pantry Cloud...")

# Auto-refresh mechanism (Polling)
if st.button("Force Check Queue"):
    process_queue()

# Auto-Runner (Loop)
# Streamlit auto-refresh ke liye hum sleep use karenge
placeholder = st.empty()

while True:
    process_queue()
    
    # Show Status Table
    statuses = get_basket(STATUS_BASKET)
    with placeholder.container():
        if statuses:
            st.write(f"### Active Tasks ({len(statuses)})")
            st.json(statuses)
        else:
            st.info("No active tasks.")
    
    time.sleep(10) # Check every 10 seconds
