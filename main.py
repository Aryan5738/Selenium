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
from selenium.webdriver.common.action_chains import ActionChains

# --- PAGE CONFIG ---
st.set_page_config(page_title="FB Ultra Sticker Sender", layout="wide")
st.title("🚀 FB Pro Sticker Bot (Live Status)")

@st.cache_resource
class TaskManager:
    def __init__(self):
        self.tasks = {}

    def create_task(self):
        task_id = str(uuid.uuid4())[:6].upper()
        self.tasks[task_id] = {
            "status": "Initializing...",
            "logs": [],
            "count": 0,
            "stop": False,
            "last_action": "None",
            "start_time": datetime.datetime.now().strftime("%I:%M %p")
        }
        return task_id

    def log(self, task_id, msg):
        if task_id in self.tasks:
            t = datetime.datetime.now().strftime("%H:%M:%S")
            self.tasks[task_id]["logs"].append(f"[{t}] {msg}")
            self.tasks[task_id]["last_action"] = msg

manager = TaskManager()

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new") # Modern headless
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Common paths for Streamlit/Linux
    service = Service(shutil.which("chromedriver") or "/usr/bin/chromedriver")
    try:
        driver = webdriver.Chrome(service=service, options=chrome_options)
        return driver
    except:
        return None

def send_sticker_flow(driver, task_id):
    try:
        # 1. Open Sticker Panel
        wait = WebDriverWait(driver, 10)
        sticker_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[@aria-label='Choose a sticker'] | //div[@aria-label='Stickers']")))
        
        # Force Click using JavaScript
        driver.execute_script("arguments[0].click();", sticker_btn)
        manager.log(task_id, "Sticker panel opened.")
        time.sleep(3)

        # 2. Get All Visible Stickers
        # Hum generic selectors use kar rahe hain jo FB ke update ke baad bhi kaam karein
        sticker_elements = driver.find_elements(By.CSS_SELECTOR, "div[role='gridcell'] img, img[src*='sticker']")
        
        if not sticker_elements:
            manager.log(task_id, "No stickers detected! Refreshing...")
            return False

        # 3. Randomly select one and Click + Enter
        choice = random.choice(sticker_elements[:15]) # Pick from top 15
        
        # Move mouse and click to simulate real human
        actions = ActionChains(driver)
        actions.move_to_element(choice).click().perform()
        
        # Extra step: Kuch cases mein select karne ke baad Enter dabana padta hai
        actions.send_keys(Keys.ENTER).perform()
        
        return True
    except Exception as e:
        manager.log(task_id, f"Error in sending: {str(e)[:40]}")
        return False

def worker(task_id, cookies, url, delay, infinite):
    driver = get_driver()
    if not driver:
        manager.tasks[task_id]["status"] = "Driver Error"
        return

    try:
        manager.log(task_id, "Setting up session...")
        driver.get("https://www.facebook.com")
        for c in cookies.split(';'):
            if '=' in c:
                name, val = c.strip().split('=', 1)
                driver.add_cookie({'name': name, 'value': val, 'domain': '.facebook.com'})
        
        manager.log(task_id, "Opening Chat...")
        driver.get(url)
        time.sleep(10) # Heavy loading time
        
        manager.tasks[task_id]["status"] = "Running ✅"

        while not manager.tasks[task_id]["stop"]:
            success = send_sticker_flow(driver, task_id)
            if success:
                manager.tasks[task_id]["count"] += 1
                manager.log(task_id, f"Sticker #{manager.tasks[task_id]['count']} Sent Successfully!")
            
            if not infinite: break
            
            # Smart Sleep: random delay thoda sa variation ke liye
            time.sleep(delay + random.randint(1, 5))
            
    except Exception as e:
        manager.log(task_id, "Fatal crash. Stopping...")
    finally:
        driver.quit()
        manager.tasks[task_id]["status"] = "Finished/Stopped"

# --- UI INTERFACE ---
col_main, col_side = st.columns([2, 1])

with col_side:
    st.markdown("### ⚙️ Settings")
    cookie_str = st.text_area("Paste Cookies", placeholder="c_user=...; xs=...", height=150)
    chat_url = st.text_input("Target URL", placeholder="https://www.facebook.com/messages/t/...")
    delay = st.number_input("Delay (Seconds)", 5, 3600, 15)
    inf = st.toggle("Loop Mode", True)
    
    if st.button("🚀 Start Bot", use_container_width=True):
        if cookie_str and chat_url:
            tid = manager.create_task()
            threading.Thread(target=worker, args=(tid, cookie_str, chat_url, delay, inf)).start()
            st.success(f"Task ID: {tid} Started!")
        else:
            st.error("Fields missing!")

with col_main:
    st.markdown("### 📊 Live Dashboard")
    task_id_input = st.text_input("Enter Task ID to view", placeholder="Example: A1B2C3")
    
    if task_id_input:
        task = manager.get_task(task_id_input.upper())
        if task:
            # Metrics
            m1, m2, m3 = st.columns(3)
            m1.metric("Status", task["status"])
            m2.metric("Sent", f"{task['count']} Stickers")
            m3.metric("Started At", task["start_time"])
            
            st.info(f"**Last Action:** {task['last_action']}")
            
            with st.expander("Full Action Logs", expanded=True):
                st.code("\n".join(task["logs"][-20:])) # Show last 20
                
            if st.button("🛑 Stop Process", type="primary"):
                manager.tasks[task_id_input.upper()]["stop"] = True
        else:
            st.warning("Task ID not found.")
        
