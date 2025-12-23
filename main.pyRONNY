import os
import time
import shutil
import threading
import uuid
import datetime
import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

# --- PAGE CONFIG ---
st.set_page_config(page_title="Background FB Sender", layout="centered")
st.title("FB Sender (Background Mode 🚀)")

# --- GLOBAL TASK MANAGER (The Brain) ---
# यह function ensure करता है कि डेटा browser बंद होने पर भी memory में रहे
@st.cache_resource
class TaskManager:
    def __init__(self):
        self.tasks = {}  # Stores all tasks: {id: {status, logs, count, stop_signal}}

    def create_task(self):
        task_id = str(uuid.uuid4())[:8]  # Short unique ID
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
            self.tasks[task_id]["status"] = "Stopped by User"

# Initialize Manager
manager = TaskManager()

# --- SELENIUM HELPERS ---
def parse_cookies(cookie_string):
    cookies = []
    try:
        items = cookie_string.split(';')
        for item in items:
            if '=' in item:
                name, value = item.strip().split('=', 1)
                cookies.append({'name': name, 'value': value, 'domain': '.facebook.com'})
        return cookies
    except:
        return []

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    
    chromium_path = shutil.which("chromium")
    chromedriver_path = shutil.which("chromedriver")
    
    if not chromium_path or not chromedriver_path:
        if os.path.exists("/usr/bin/chromium"): chromium_path = "/usr/bin/chromium"
        if os.path.exists("/usr/bin/chromedriver"): chromedriver_path = "/usr/bin/chromedriver"

    if chromium_path and chromedriver_path:
        chrome_options.binary_location = chromium_path
        service = Service(chromedriver_path)
        try:
            return webdriver.Chrome(service=service, options=chrome_options)
        except Exception:
            return None
    return None

def hunt_down_buttons(driver, task_id):
    # Log to global manager instead of st.write
    # manager.log_update(task_id, "Scanning for popups...")
    try:
        xpaths = [
            "//div[@role='button']//span[contains(text(), 'Continue')]",
            "//*[contains(text(), 'restore messages')]",
            "//div[@aria-label='Continue']",
            "//div[@aria-label='Close']"
        ]
        for xpath in xpaths:
            btns = driver.find_elements(By.XPATH, xpath)
            for btn in btns:
                if btn.is_displayed():
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(1)
    except:
        pass

def send_message_safely(driver, text):
    selectors = ['div[aria-label="Message"]', 'div[contenteditable="true"]', 'div[role="textbox"]']
    msg_box = None
    for selector in selectors:
        try:
            msg_box = driver.find_element(By.CSS_SELECTOR, selector)
            if msg_box: break
        except:
            continue
            
    if msg_box:
        try:
            driver.execute_script("arguments[0].focus();", msg_box)
            actions = ActionChains(driver)
            actions.send_keys(text)
            actions.send_keys(Keys.RETURN)
            actions.perform()
            return True
        except:
            return False
    return False

# --- BACKGROUND WORKER ---
def run_background_task(task_id, cookie_str, url, msg, delay, is_infinite):
    manager.log_update(task_id, "Starting Driver...")
    driver = get_driver()
    
    if not driver:
        manager.log_update(task_id, "Error: Driver Failed")
        manager.tasks[task_id]["status"] = "Failed"
        return

    try:
        driver.get("https://www.facebook.com/")
        cookies = parse_cookies(cookie_str)
        for c in cookies:
            try: driver.add_cookie(c)
            except: pass
        
        manager.log_update(task_id, "Navigating to Chat...")
        driver.get(url)
        time.sleep(8)
        
        hunt_down_buttons(driver, task_id)
        
        keep_running = True
        while keep_running:
            # CHECK STOP SIGNAL
            if manager.tasks[task_id]["stop"]:
                manager.log_update(task_id, "Stop signal received.")
                break

            success = send_message_safely(driver, msg)
            
            if success:
                manager.tasks[task_id]["count"] += 1
                current_count = manager.tasks[task_id]["count"]
                manager.log_update(task_id, f"Sent Message #{current_count}")
                
                if not is_infinite:
                    keep_running = False
                    manager.tasks[task_id]["status"] = "Completed"
                else:
                    time.sleep(delay)
            else:
                manager.log_update(task_id, "Send Failed. Retrying...")
                time.sleep(5)
                hunt_down_buttons(driver, task_id)

    except Exception as e:
        manager.log_update(task_id, f"Error: {str(e)}")
        manager.tasks[task_id]["status"] = "Error"
    finally:
        driver.quit()
        if manager.tasks[task_id]["status"] == "Running":
            manager.tasks[task_id]["status"] = "Finished"

# --- UI TABS ---
tab1, tab2 = st.tabs(["🆕 New Task", "🔍 Check Status"])

# TAB 1: CREATE TASK
with tab1:
    st.subheader("Start New Automation")
    cookie_input = st.text_area("Cookie", height=70)
    target_url = st.text_input("Chat URL", "https://www.facebook.com/messages/e2ee/...")
    message_text = st.text_input("Message", "Hello!")
    
    c1, c2 = st.columns(2)
    enable_infinite = c1.checkbox("Infinite Loop", False)
    delay_time = c2.number_input("Delay (sec)", 2, 60, 2)

    if st.button("🚀 Start Background Task"):
        if not cookie_input or not target_url:
            st.error("Please fill all fields")
        else:
            # 1. Create ID
            new_id = manager.create_task()
            
            # 2. Start Thread
            t = threading.Thread(
                target=run_background_task, 
                args=(new_id, cookie_input, target_url, message_text, delay_time, enable_infinite)
            )
            t.start()
            
            # 3. Show User
            st.success(f"Task Started! Your ID is: **{new_id}**")
            st.info("⚠️ Copy this ID. You can close the browser now. Come back and check status in 'Check Status' tab.")

# TAB 2: CHECK STATUS
with tab2:
    st.subheader("Monitor Task")
    check_id = st.text_input("Enter Task ID")
    
    if st.button("Check Progress") or check_id:
        task_data = manager.get_task(check_id)
        
        if task_data:
            st.write(f"**Status:** {task_data['status']}")
            st.write(f"**Messages Sent:** {task_data['count']}")
            st.write(f"**Start Time:** {task_data['start_time']}")
            
            with st.expander("View Logs", expanded=True):
                # Show last 10 logs
                for log in task_data['logs'][-10:]:
                    st.text(log)
            
            if task_data['status'] == "Running":
                if st.button("🛑 Stop Task"):
                    manager.stop_task(check_id)
                    st.rerun()
        else:
            if check_id:
                st.error("Task ID not found or server restarted.")

