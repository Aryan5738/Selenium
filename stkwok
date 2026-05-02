import os
import time
import shutil
import threading
import uuid
import datetime
import random
import base64
import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- CONFIG ---
st.set_page_config(page_title="24/7 Shiba Sniper Pro", layout="wide")

# Global Manager Class (Fixed)
class GlobalTaskManager:
    def __init__(self):
        self.tasks = {}

    def create_task(self):
        tid = str(uuid.uuid4())[:6].upper()
        self.tasks[tid] = {"status": "Starting...", "logs": [], "count": 0, "stop": False, "last_screenshot": None}
        return tid

    def get_task(self, tid):
        # Yeh line error fixed: check if tid exists
        return self.tasks.get(tid)

    def update_log(self, tid, msg, driver=None):
        if tid in self.tasks:
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            self.tasks[tid]["logs"].append(f"[{ts}] {msg}")
            if driver:
                try:
                    self.tasks[tid]["last_screenshot"] = driver.get_screenshot_as_base64()
                except:
                    pass

# Cache the manager so it persists across refreshes
@st.cache_resource
def get_manager():
    return GlobalTaskManager()

manager = get_manager()
SHIBA_IDS = ["212482136326646", "219662825608577", "212483102993216", "1747083982269520", "219665422274984"]

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    service = Service(shutil.which("chromedriver") or "/usr/bin/chromedriver")
    return webdriver.Chrome(service=service, options=chrome_options)

def send_logic(driver, tid, s_id):
    try:
        # Delete popups
        driver.execute_script("document.querySelectorAll('div[role=\"dialog\"], div[aria-label*=\"PIN\"], div[aria-label*=\"restore\"]').forEach(el => el.remove());")
        wait = WebDriverWait(driver, 10)
        icon = wait.until(EC.presence_of_element_located((By.XPATH, "//div[@aria-label='Choose a sticker'] | //i[contains(@style, 'stickers')]")))
        driver.execute_script("arguments[0].click();", icon)
        time.sleep(7)
        
        inject = f"""
        var id = "{s_id}";
        var el = document.querySelector('img[src*="' + id + '"]');
        if (el) {{
            var r = el.getBoundingClientRect();
            var e = new MouseEvent('click', {{view:window, bubbles:true, clientX:r.left+r.width/2, clientY:r.top+r.height/2}});
            el.dispatchEvent(e);
            return true;
        }}
        return false;
        """
        if driver.execute_script(inject):
            time.sleep(1)
            driver.execute_script("window.dispatchEvent(new KeyboardEvent('keydown', {'key': 'Enter'}));")
            return True
        return False
    except: return False

def worker(tid, cookies, url, delay):
    while not manager.get_task(tid)["stop"]:
        driver = get_driver()
        try:
            manager.update_log(tid, "Session Starting...")
            driver.get("https://www.facebook.com")
            for c in cookies.split(';'):
                if '=' in c:
                    n, v = c.strip().split('=', 1)
                    driver.add_cookie({'name': n.strip(), 'value': v.strip(), 'domain': '.facebook.com'})
            
            driver.get(url)
            time.sleep(15)
            manager.tasks[tid]["status"] = "Running 24/7 ✅"
            
            local_count = 0
            while not manager.tasks[tid]["stop"] and local_count < 50:
                sid = random.choice(SHIBA_IDS)
                if send_logic(driver, tid, sid):
                    manager.tasks[tid]["count"] += 1
                    local_count += 1
                    manager.update_log(tid, f"💥 Sent Shiba #{manager.tasks[tid]['count']}", driver)
                else:
                    manager.update_log(tid, "UI Lag... Retrying", driver)
                    driver.refresh()
                    time.sleep(10)
                time.sleep(delay)
            driver.quit()
        except:
            try: driver.quit()
            except: pass
            time.sleep(10)

# --- UI ---
st.title("🛡️ FB Sniper (never-stop fixed)")
c1, c2 = st.columns([1, 2])

with c1:
    ck = st.text_area("Cookies")
    target = st.text_input("URL")
    spd = st.number_input("Delay", 10, 600, 25)
    if st.button("Start Bot"):
        tid = manager.create_task()
        threading.Thread(target=worker, args=(tid, ck, target, spd)).start()
        st.success(f"Task ID: {tid}")

with c2:
    search = st.text_input("Enter ID to Track").upper()
    if search:
        task_data = manager.get_task(search)
        if task_data:
            st.metric("Sent", task_data["count"])
            if task_data["last_screenshot"]:
                st.image(base64.b64decode(task_data["last_screenshot"]), use_container_width=True)
            st.code("\n".join(task_data["logs"][-15:]))
            if st.button("Stop"): task_data["stop"] = True
                   
