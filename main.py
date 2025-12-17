import uvicorn
import threading
import uuid
import time
import os
import shutil
import datetime
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

# --- APP SETUP ---
app = FastAPI(title="FB Auto Sender API")

# --- GLOBAL STORAGE (In-Memory Database) ---
# Format: { "task_id": { "status": "...", "logs": [], "count": 0, "stop": False } }
tasks = {}

# --- INPUT MODEL ---
class TaskInput(BaseModel):
    cookie: str
    url: str
    message: str
    delay: int = 2
    infinite: bool = False

# --- SELENIUM HELPERS ---
def get_driver():
    """Starts Headless Chrome Driver"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    
    # Auto-detect paths (Works on Linux/Cloud/PC)
    chromium_path = shutil.which("chromium")
    chromedriver_path = shutil.which("chromedriver")
    
    # Manual Fallback for Cloud Servers
    if not chromium_path: 
        if os.path.exists("/usr/bin/chromium"): chromium_path = "/usr/bin/chromium"
    if not chromedriver_path:
        if os.path.exists("/usr/bin/chromedriver"): chromedriver_path = "/usr/bin/chromedriver"

    if chromium_path and chromedriver_path:
        chrome_options.binary_location = chromium_path
        service = Service(chromedriver_path)
        try:
            return webdriver.Chrome(service=service, options=chrome_options)
        except Exception as e:
            print(f"Driver Init Error: {e}")
            return None
    return None

def parse_cookies(cookie_string):
    """Converts string cookies to list"""
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

def send_message_safely(driver, text):
    """Safe Send Logic (Bypasses Interception)"""
    try:
        selectors = ['div[aria-label="Message"]', 'div[role="textbox"]', 'div[contenteditable="true"]']
        msg_box = None
        for s in selectors:
            try: 
                msg_box = driver.find_element(By.CSS_SELECTOR, s)
                if msg_box: break
            except: continue
        
        if msg_box:
            driver.execute_script("arguments[0].focus();", msg_box)
            actions = ActionChains(driver)
            actions.send_keys(text)
            actions.send_keys(Keys.RETURN)
            actions.perform()
            return True
    except:
        return False
    return False

def hunt_popups(driver):
    """Closes 'Continue' or 'Restore' popups"""
    try:
        btns = driver.find_elements(By.XPATH, "//div[@role='button']//span[contains(text(), 'Continue')]")
        for btn in btns: driver.execute_script("arguments[0].click();", btn)
    except: pass

# --- BACKGROUND WORKER ---
def worker_process(task_id: str, data: TaskInput):
    """The Logic that runs in background"""
    tasks[task_id]["status"] = "Initializing Driver..."
    driver = get_driver()
    
    if not driver:
        tasks[task_id]["status"] = "Failed: Driver Config Error"
        tasks[task_id]["logs"].append("Error: Chromium/Driver not found.")
        return

    try:
        # 1. Login
        tasks[task_id]["logs"].append("Opening Facebook...")
        driver.get("https://www.facebook.com/")
        
        cookies = parse_cookies(data.cookie)
        for c in cookies:
            try: driver.add_cookie(c)
            except: pass
            
        # 2. Open Chat
        tasks[task_id]["status"] = "Navigating..."
        tasks[task_id]["logs"].append(f"Opening Chat URL...")
        driver.get(data.url)
        time.sleep(8) # Wait for page load
        
        hunt_popups(driver)
        tasks[task_id]["status"] = "Running"
        
        # 3. Loop
        keep_running = True
        while keep_running:
            # Check Stop Signal
            if tasks[task_id]["stop"]:
                tasks[task_id]["logs"].append("Stop signal received.")
                break
            
            # Send
            if send_message_safely(driver, data.message):
                tasks[task_id]["count"] += 1
                cnt = tasks[task_id]["count"]
                timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                tasks[task_id]["logs"].append(f"[{timestamp}] Sent Msg #{cnt} ✅")
                
                # Infinite Check
                if not data.infinite:
                    tasks[task_id]["status"] = "Completed"
                    keep_running = False
                else:
                    time.sleep(data.delay)
            else:
                tasks[task_id]["logs"].append("⚠️ Failed to send (Popup?). Retrying...")
                hunt_popups(driver)
                time.sleep(5)
                
    except Exception as e:
        tasks[task_id]["status"] = "Error"
        tasks[task_id]["logs"].append(f"Critical Error: {str(e)}")
    finally:
        driver.quit()
        if tasks[task_id]["status"] == "Running":
            tasks[task_id]["status"] = "Stopped"

# --- API ENDPOINTS ---

@app.get("/")
def home():
    return {"status": "Online", "message": "FB Auto Sender API is Ready 🚀"}

@app.post("/start_task")
def start_task(data: TaskInput, background_tasks: BackgroundTasks):
    """Creates a new task and runs it in background"""
    task_id = str(uuid.uuid4())[:8]
    
    # Init State
    tasks[task_id] = {
        "status": "Queued",
        "count": 0,
        "logs": ["Task created."],
        "stop": False,
        "start_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Hand over to background worker
    background_tasks.add_task(worker_process, task_id, data)
    
    return {"task_id": task_id, "message": "Background task started successfully"}

@app.get("/status/{task_id}")
def check_status(task_id: str):
    """Returns live status of a task"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task ID not found")
    return tasks[task_id]

@app.post("/stop/{task_id}")
def stop_task(task_id: str):
    """Stops a running task"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task ID not found")
    
    tasks[task_id]["stop"] = True
    return {"message": "Stop signal sent to worker"}

# --- RUNNER ---
if __name__ == "__main__":
    # Runs the server on port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)
