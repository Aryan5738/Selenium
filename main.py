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

# --- PAGE CONFIG ---
st.set_page_config(page_title="FB Shiba 24/7 Sniper", layout="wide")

@st.cache_resource
class GlobalTaskManager:
    def __init__(self):
        self.tasks = {}

    def create_task(self):
        tid = str(uuid.uuid4())[:6].upper()
        self.tasks[tid] = {"status": "Starting...", "logs": [], "count": 0, "stop": False, "last_screenshot": None}
        return tid

    def get_task(self, tid): return self.tasks.get(tid)

    def update_log(self, tid, msg, driver=None):
        if tid in self.tasks:
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            self.tasks[tid]["logs"].append(f"[{ts}] {msg}")
            if driver:
                try: self.tasks[tid]["last_screenshot"] = driver.get_screenshot_as_base64()
                except: pass

manager = GlobalTaskManager()

# --- FIXED SHIBA IDS ---
SHIBA_IDS = [
    "212482136326646", 
    "219662825608577", 
    "212483102993216", 
    "1747083982269520", 
    "219665422274984"
]

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    service = Service(shutil.which("chromedriver") or "/usr/bin/chromedriver")
    return webdriver.Chrome(service=service, options=chrome_options)

def shiba_sniper_logic(driver, tid):
    try:
        # Delete popups from HTML
        driver.execute_script("document.querySelectorAll('div[role=\"dialog\"], div[aria-label*=\"PIN\"], div[aria-label*=\"restore\"]').forEach(el => el.remove());")
        
        # Open Panel
        wait = WebDriverWait(driver, 10)
        icon_xpath = "//div[@aria-label='Choose a sticker'] | //i[contains(@style, 'stickers')]"
        icon = wait.until(EC.presence_of_element_located((By.XPATH, icon_xpath)))
        driver.execute_script("arguments[0].click();", icon)
        time.sleep(7)

        # Randomly select an ID from our pack
        current_id = random.choice(SHIBA_IDS)
        
        # Dispatcher Script
        script = f"""
        var targetId = "{current_id}";
        var found = false;
        var imgs = document.querySelectorAll('img');
        for (var i = 0; i < imgs.length; i++) {{
            if (imgs[i].src.includes(targetId)) {{
                var el = imgs[i];
                var rect = el.getBoundingClientRect();
                var ev = new MouseEvent('click', {{
                    view: window, bubbles: true, cancelable: true,
                    clientX: rect.left + rect.width/2, clientY: rect.top + rect.height/2
                }});
                el.dispatchEvent(ev);
                found = true; break;
            }}
        }}
        return found;
        """
        success = driver.execute_script(script)
        if success:
            time.sleep(1)
            driver.execute_script("window.dispatchEvent(new KeyboardEvent('keydown', {'key': 'Enter'}));")
            return True
        return False
    except: return False

def worker(tid, cookies, url, delay):
    driver = get_driver()
    try:
        driver.get("https://www.facebook.com")
        for c in cookies.split(';'):
            if '=' in c:
                n, v = c.strip().split('=', 1)
                driver.add_cookie({'name': n.strip(), 'value': v.strip(), 'domain': '.facebook.com'})
        
        driver.get(url)
        time.sleep(15)
        manager.tasks[tid]["status"] = "Active 🚀"

        while not manager.tasks[tid]["stop"]:
            if driver.current_url != url:
                driver.get(url)
                time.sleep(8)

            if shiba_sniper_logic(driver, tid):
                manager.tasks[tid]["count"] += 1
                manager.update_log(tid, f"💥 Sent Shiba #{manager.tasks[tid]['count']}")
            else:
                manager.update_log(tid, "UI Lag... Refreshing.")
                driver.refresh()
                time.sleep(12)

            time.sleep(delay)
    finally:
        driver.quit()
        manager.tasks[tid]["status"] = "Stopped"

# --- UI ---
st.title("🔥 Shiba Sniper 24/7 Edition")
c1, c2 = st.columns([1, 2])

with c1:
    ck = st.text_area("Cookies")
    target = st.text_input("Chat Link")
    spd = st.slider("Interval (Sec)", 10, 300, 20)
    if st.button("🚀 Start Bot"):
        tid = manager.create_task()
        threading.Thread(target=worker, args=(tid, ck, target, spd)).start()
        st.success(f"Running! Task ID: {tid}")

with c2:
    search = st.text_input("Monitor ID").upper()
    if search and manager.get_task(search):
        data = manager.get_task(search)
        st.metric("Stickers Sent", data["count"])
        if data["last_screenshot"]:
            st.image(base64.decodebytes(data["last_screenshot"].encode()), use_container_width=True)
        st.code("\n".join(data["logs"][-15:]))
        
