import streamlit as st
import threading
import uuid
import time
import json
import os
import shutil
import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

# --- PAGE CONFIG ---
st.set_page_config(page_title="FB API Bot", layout="wide")

# --- GLOBAL MEMORY ---
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
            "start_time": datetime.datetime.now().strftime("%H:%M:%S")
        }
        return task_id

    def get_task(self, task_id):
        return self.tasks.get(task_id)

    def log(self, task_id, msg):
        if task_id in self.tasks:
            self.tasks[task_id]["logs"].append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}")

manager = TaskManager()

# --- SELENIUM ---
def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    
    path_chromium = shutil.which("chromium") or "/usr/bin/chromium"
    path_driver = shutil.which("chromedriver") or "/usr/bin/chromedriver"

    if os.path.exists(path_chromium) and os.path.exists(path_driver):
        chrome_options.binary_location = path_chromium
        service = Service(path_driver)
        try:
            return webdriver.Chrome(service=service, options=chrome_options)
        except: return None
    return None

def run_worker(task_id, cookie, url, msg, delay, infinite):
    manager.log(task_id, "Starting Driver...")
    driver = get_driver()
    if not driver:
        manager.tasks[task_id]["status"] = "Failed"
        return

    try:
        driver.get("https://www.facebook.com/")
        try:
            items = cookie.split(';')
            for item in items:
                if '=' in item:
                    name, value = item.strip().split('=', 1)
                    driver.add_cookie({'name': name, 'value': value, 'domain': '.facebook.com'})
        except: pass
        
        manager.log(task_id, "Navigating...")
        driver.get(url)
        time.sleep(8)
        
        # Popup Hunter
        try:
            btns = driver.find_elements(By.XPATH, "//div[@role='button']//span[contains(text(), 'Continue')]")
            for btn in btns: driver.execute_script("arguments[0].click();", btn)
        except: pass

        while not manager.tasks[task_id]["stop"]:
            try:
                # Find Box
                box = driver.find_element(By.CSS_SELECTOR, 'div[aria-label="Message"], div[role="textbox"]')
                driver.execute_script("arguments[0].focus();", box)
                actions = ActionChains(driver)
                actions.send_keys(msg)
                actions.send_keys(Keys.RETURN)
                actions.perform()
                
                manager.tasks[task_id]["count"] += 1
                manager.log(task_id, f"Sent #{manager.tasks[task_id]['count']}")
                
                if not infinite:
                    manager.tasks[task_id]["status"] = "Completed"
                    break
                time.sleep(int(delay))
            except:
                time.sleep(5)
                # Retry Popup Hunter
                try:
                    btns = driver.find_elements(By.XPATH, "//div[@role='button']//span[contains(text(), 'Continue')]")
                    for btn in btns: driver.execute_script("arguments[0].click();", btn)
                except: pass

    except Exception as e:
        manager.log(task_id, f"Error: {str(e)}")
        manager.tasks[task_id]["status"] = "Error"
    finally:
        driver.quit()

# --- 🔥 API HACK LOGIC ---
# We check URL parameters. If 'api_mode' is present, we act as API.

params = st.query_params

if "api_mode" in params:
    mode = params.get("mode")
    
    # 1. START TASK
    if mode == "start":
        try:
            cookie = params.get("cookie")
            url = params.get("url")
            msg = params.get("msg")
            delay = params.get("delay", 2)
            infinite = params.get("infinite") == "true"
            
            new_id = manager.create_task()
            t = threading.Thread(target=run_worker, args=(new_id, cookie, url, msg, delay, infinite))
            t.start()
            
            response = {"status": "success", "task_id": new_id}
        except Exception as e:
            response = {"status": "error", "message": str(e)}

    # 2. CHECK STATUS
    elif mode == "status":
        tid = params.get("tid")
        task = manager.get_task(tid)
        if task:
            response = task
        else:
            response = {"error": "Task not found"}
            
    # 3. STOP TASK
    elif mode == "stop":
        tid = params.get("tid")
        if tid in manager.tasks:
            manager.tasks[tid]["stop"] = True
            response = {"status": "stopped"}
        else:
            response = {"error": "Invalid ID"}
    
    else:
        response = {"error": "Unknown command"}

    # --- MAGIC TRICK: Hide JSON in HTML ---
    # Termux will regex search for API_START {json} API_END
    st.markdown(f"", unsafe_allow_html=True)
    st.write("API Request Processed.")
    st.stop() # Stop rendering the rest of the UI

# --- NORMAL UI (For Web) ---
st.title("FB Auto Sender (Web Interface)")
st.write("Termux API Endpoint Active.")
                                               
