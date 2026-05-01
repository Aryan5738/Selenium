import os
import time
import shutil
import threading
import uuid
import datetime
import random
import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- PAGE CONFIG ---
st.set_page_config(page_title="Multi-Sticker FB Sender", layout="centered")
st.title("FB Multi-Sticker Bot 🚀")

@st.cache_resource
class TaskManager:
    def __init__(self):
        self.tasks = {}

    def create_task(self):
        task_id = str(uuid.uuid4())[:8]
        self.tasks[task_id] = {
            "status": "Running",
            "logs": [],
            "count": 0,
            "stop": False,
            "start_time": datetime.datetime.now()
        }
        return task_id

    def get_task(self, task_id):
        return self.tasks.get(task_id)

    def log_update(self, task_id, message):
        if task_id in self.tasks:
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            self.tasks[task_id]["logs"].append(f"[{timestamp}] {message}")

    def stop_task(self, task_id):
        if task_id in self.tasks:
            self.tasks[task_id]["stop"] = True
            self.tasks[task_id]["status"] = "Stopped"

manager = TaskManager()

# --- SELENIUM HELPERS ---
def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    chromedriver_path = shutil.which("chromedriver") or "/usr/bin/chromedriver"
    chromium_path = shutil.which("chromium") or "/usr/bin/chromium"

    if os.path.exists(chromedriver_path):
        chrome_options.binary_location = chromium_path
        service = Service(chromedriver_path)
        return webdriver.Chrome(service=service, options=chrome_options)
    return None

def send_random_sticker(driver, task_id):
    try:
        # 1. Sticker Icon dhoondna aur click karna
        sticker_icons = [
            "//div[@aria-label='Choose a sticker']",
            "//div[@aria-label='Stickers']",
            "//span[contains(@class, 'x10l6tqk')]//div[@role='button']"
        ]
        
        btn = None
        for xpath in sticker_icons:
            try:
                btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, xpath)))
                if btn: break
            except: continue
        
        if btn:
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(3) # Panel load hone ka wait
            
            # 2. Saare visible stickers ki list nikalna
            # Hum image tags ya gridcells ko target karte hain
            stickers = driver.find_elements(By.CSS_SELECTOR, "div[role='gridcell'] img, img[src*='static.xx.fbcdn.net/rsrc.php/v3']")
            
            if stickers:
                # Randomly ek sticker select karna list se (e.g., pehle 10 mein se)
                max_choice = min(len(stickers), 12)
                random_index = random.randint(0, max_choice - 1)
                target_sticker = stickers[random_index]
                
                manager.log_update(task_id, f"Selecting sticker variation #{random_index + 1}")
                driver.execute_script("arguments[0].click();", target_sticker)
                return True
            else:
                manager.log_update(task_id, "No stickers found in the panel.")
        return False
    except Exception as e:
        manager.log_update(task_id, f"Sticker Send Error: {str(e)[:50]}")
        return False

# --- BACKGROUND WORKER ---
def run_background_task(task_id, cookie_str, url, delay, is_infinite):
    manager.log_update(task_id, "Starting background driver...")
    driver = get_driver()
    
    if not driver:
        manager.log_update(task_id, "Driver Error: Check environment setup.")
        manager.tasks[task_id]["status"] = "Failed"
        return

    try:
        driver.get("https://www.facebook.com/")
        for item in cookie_str.split(';'):
            if '=' in item:
                name, value = item.strip().split('=', 1)
                driver.add_cookie({'name': name, 'value': value, 'domain': '.facebook.com'})
        
        manager.log_update(task_id, "Navigating to Chat...")
        driver.get(url)
        time.sleep(8)
        
        while not manager.tasks[task_id]["stop"]:
            success = send_random_sticker(driver, task_id)
            
            if success:
                manager.tasks[task_id]["count"] += 1
                manager.log_update(task_id, f"✅ Done: Total {manager.tasks[task_id]['count']} multi-stickers sent.")
                if not is_infinite: break
                time.sleep(delay)
            else:
                manager.log_update(task_id, "Trying to refresh UI...")
                driver.refresh()
                time.sleep(10)

    except Exception as e:
        manager.log_update(task_id, f"Fatal Error: {str(e)}")
    finally:
        driver.quit()
        if manager.tasks[task_id]["status"] == "Running":
            manager.tasks[task_id]["status"] = "Completed"

# --- STREAMLIT UI ---
tab1, tab2 = st.tabs(["🚀 Start Task", "📊 Monitor"])

with tab1:
    cookies = st.text_area("FB Cookies (c_user=...; xs=...;)", height=100)
    chat_url = st.text_input("Messenger Chat URL", placeholder="https://www.facebook.com/messages/t/...")
    
    col1, col2 = st.columns(2)
    loop = col1.checkbox("Infinite Sending", value=True)
    wait_time = col2.number_input("Wait between stickers (sec)", 5, 600, 20)

    if st.button("Launch Multi-Sticker Bot"):
        if cookies and chat_url:
            new_id = manager.create_task()
            threading.Thread(target=run_background_task, args=(new_id, cookies, chat_url, wait_time, loop)).start()
            st.success(f"Task Launched! ID: {new_id}")
        else:
            st.warning("Please fill in Cookies and Chat URL.")

with tab2:
    search_id = st.text_input("Check ID Status")
    if search_id:
        task = manager.get_task(search_id)
        if task:
            st.metric("Total Stickers Sent", task["count"])
            st.info(f"Current Status: {task['status']}")
            with st.expander("Live Logs"):
                st.code("\n".join(task["logs"]))
            if st.button("Stop Process"):
                manager.stop_task(search_id)
                st.rerun()
        else:
            st.error("Task ID not found.")
                
