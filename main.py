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
st.set_page_config(page_title="FB Nuclear Sticker Bot", layout="wide")

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

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    # Stealth mode settings
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    service = Service(shutil.which("chromedriver") or "/usr/bin/chromedriver")
    return webdriver.Chrome(service=service, options=chrome_options)

def nuclear_sticker_send(driver, tid):
    try:
        wait = WebDriverWait(driver, 15)
        
        # 1. Sabse pehle PIN/Restore popups ko uda do (Zaroori hai)
        driver.execute_script("""
            var popups = document.querySelectorAll('div[role="dialog"], div[aria-label*="PIN"], div[aria-label*="restore"]');
            popups.forEach(p => p.remove());
            var overlays = document.querySelectorAll('div[style*="background-color: rgba(0, 0, 0, 0.5)"]');
            overlays.forEach(o => o.remove());
        """)

        # 2. Open Sticker Panel
        icon_xpath = "//div[@aria-label='Choose a sticker'] | //i[contains(@style, 'stickers')]"
        sticker_btn = wait.until(EC.presence_of_element_located((By.XPATH, icon_xpath)))
        driver.execute_script("arguments[0].click();", sticker_btn)
        
        manager.update_log(tid, "Sticker panel opened. Force-loading grid...", driver)
        time.sleep(10) # Heavy wait for E2EE decryption

        # 3. NUCLEAR JUGAD: Direct DOM Injection
        # Hum sticker image par click nahi karenge, hum browser ko bolenge ki us image ka 'native' click event fire kare
        stickers = driver.find_elements(By.CSS_SELECTOR, "div[role='gridcell'] img, img[alt*='sticker']")
        
        if stickers:
            target_sticker = random.choice(stickers[:10])
            manager.update_log(tid, "Targeting Sticker via Native Dispatch...", driver)
            
            # Ye script Facebook ke internal event listeners ko trigger karegi
            nuclear_script = """
            var el = arguments[0];
            var box = el.getBoundingClientRect();
            var x = box.left + box.width / 2;
            var y = box.top + box.height / 2;

            function fire(type) {
                var e = new MouseEvent(type, {
                    view: window,
                    bubbles: true,
                    cancelable: true,
                    clientX: x,
                    clientY: y,
                    buttons: 1
                });
                el.dispatchEvent(e);
            }

            el.focus();
            fire('mouseover');
            fire('mousedown');
            fire('mouseup');
            fire('click');
            """
            driver.execute_script(nuclear_script, target_sticker)
            
            # 4. Final Force: Enter key via browser console
            time.sleep(1)
            driver.execute_script("window.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter'}));")
            
            return True
        return False
    except Exception as e:
        manager.update_log(tid, "Scanning UI elements...", driver)
        return False

def worker(tid, cookies, url, delay):
    driver = get_driver()
    try:
        # Standard Login
        driver.get("https://www.facebook.com")
        for c in cookies.split(';'):
            if '=' in c:
                n, v = c.strip().split('=', 1)
                driver.add_cookie({'name': n.strip(), 'value': v.strip(), 'domain': '.facebook.com'})
        
        driver.get(url)
        time.sleep(15)
        
        manager.tasks[tid]["status"] = "Running 🚀"

        while not manager.tasks[tid]["stop"]:
            # Auto-Refresh if stuck
            if "messages" not in driver.current_url:
                driver.get(url)
                time.sleep(10)

            if nuclear_sticker_send(driver, tid):
                manager.tasks[tid]["count"] += 1
                manager.update_log(tid, f"💥 BOOM! Sticker #{manager.tasks[tid]['count']} sent.", driver)
            else:
                manager.update_log(tid, "Panel failed to respond. Refreshing page...", driver)
                driver.refresh()
                time.sleep(12)

            time.sleep(delay)
    finally:
        driver.quit()
        if tid in manager.tasks: manager.tasks[tid]["status"] = "Stopped"

# --- UI ---
st.title("🚀 FB Nuclear Sticker Bot (Final Jugad)")
col1, col2 = st.columns([1, 2])

with col1:
    ck = st.text_area("Fresh Cookies")
    chat_url = st.text_input("E2EE Chat URL")
    delay = st.slider("Delay (Sec)", 10, 300, 20)
    if st.button("🚀 Launch Nuclear Bot"):
        tid = manager.create_task()
        threading.Thread(target=worker, args=(tid, ck, chat_url, delay)).start()
        st.success(f"Task ID: {tid}")

with col2:
    search = st.text_input("Enter ID").upper()
    if search and manager.get_task(search):
        data = manager.get_task(search)
        st.metric("Total Stickers Sent", data["count"])
        if data["last_screenshot"]:
            st.image(base64.b64decode(data["last_screenshot"]), caption="Nuclear View")
        st.code("\n".join(data["logs"][-15:]))
        if st.button("Stop"): data["stop"] = True
    
