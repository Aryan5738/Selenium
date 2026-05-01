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
from selenium.webdriver.common.action_chains import ActionChains

# --- PAGE CONFIG ---
st.set_page_config(page_title="FB Ghost-Clicker Pro", layout="wide")

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
    service = Service(shutil.which("chromedriver") or "/usr/bin/chromedriver")
    return webdriver.Chrome(service=service, options=chrome_options)

def clean_blocking_ui(driver, tid):
    """PIN aur 'Restore' wale popups ko hatane ke liye"""
    popups = [
        "//div[@role='dialog']//div[@aria-label='Close']",
        "//span[contains(text(), 'restore')]",
        "//div[@aria-label='Don’t restore messages']"
    ]
    for p in popups:
        try:
            btns = driver.find_elements(By.XPATH, p)
            for b in btns:
                if b.is_displayed():
                    driver.execute_script("arguments[0].click();", b)
                    time.sleep(2)
        except: pass

def ghost_click_sticker(driver, tid):
    try:
        wait = WebDriverWait(driver, 15)
        clean_blocking_ui(driver, tid)

        # 1. Open Sticker Panel
        icon_xpath = "//div[@aria-label='Choose a sticker'] | //div[@role='button']//i[contains(@style, 'stickers')]"
        sticker_btn = wait.until(EC.presence_of_element_located((By.XPATH, icon_xpath)))
        
        # Human-like click to open
        driver.execute_script("arguments[0].click();", sticker_btn)
        manager.update_log(tid, "Sticker panel opened. Waiting for decryption...", driver)
        time.sleep(8) # Extra time for E2EE decryption

        # 2. GHOST CLICK LOGIC (JavaScript Event Simulation)
        # Hum sticker ko dhoondhenge aur uspar direct 'mousedown' aur 'mouseup' bhejenge
        stickers = driver.find_elements(By.CSS_SELECTOR, "div[role='gridcell'] img, img[alt*='sticker']")
        
        if stickers:
            target = random.choice(stickers[:min(len(stickers), 10)])
            manager.update_log(tid, "Targeting sticker with Ghost-Click...", driver)
            
            # Ye script asli mouse click ki tarah behave karti hai
            ghost_script = """
            var target = arguments[0];
            var rect = target.getBoundingClientRect();
            var x = rect.left + rect.width / 2;
            var y = rect.top + rect.height / 2;

            function triggerEvent(type) {
                var ev = new MouseEvent(type, {
                    view: window,
                    bubbles: true,
                    cancelable: true,
                    clientX: x,
                    clientY: y
                });
                target.dispatchEvent(ev);
            }

            triggerEvent('mouseover');
            triggerEvent('mousedown');
            triggerEvent('click');
            triggerEvent('mouseup');
            """
            driver.execute_script(ghost_script, target)
            
            # 3. Final Backup: Send Enter
            time.sleep(1)
            ActionChains(driver).send_keys(Keys.ENTER).perform()
            
            return True
        return False
    except Exception as e:
        manager.update_log(tid, "Searching for elements...", driver)
        return False

def worker(tid, cookies, url, delay):
    driver = get_driver()
    try:
        # Step 1: Login with Cookies
        driver.get("https://www.facebook.com")
        for c in cookies.split(';'):
            if '=' in c:
                n, v = c.strip().split('=', 1)
                driver.add_cookie({'name': n.strip(), 'value': v.strip(), 'domain': '.facebook.com'})
        
        # Step 2: Open Chat
        driver.get(url)
        time.sleep(12)
        manager.tasks[tid]["status"] = "Running ✅"

        while not manager.tasks[tid]["stop"]:
            # URL Lock
            if driver.current_url != url:
                driver.get(url)
                time.sleep(8)

            if ghost_click_sticker(driver, tid):
                manager.tasks[tid]["count"] += 1
                manager.update_log(tid, f"✅ Done! Sent #{manager.tasks[tid]['count']}", driver)
            else:
                manager.update_log(tid, "Refreshing UI...", driver)
                driver.refresh()
                time.sleep(12)

            time.sleep(delay + random.randint(3, 7))
    finally:
        driver.quit()
        if tid in manager.tasks: manager.tasks[tid]["status"] = "Stopped"

# --- STREAMLIT UI ---
st.title("🦾 FB Ghost-Clicker (Final Advanced)")
col1, col2 = st.columns([1, 2])

with col1:
    ck = st.text_area("Fresh Cookies")
    chat_url = st.text_input("E2EE Chat Link")
    wait_time = st.slider("Delay (Sec)", 10, 300, 20)
    if st.button("🚀 Start Ghost-Clicker"):
        tid = manager.create_task()
        threading.Thread(target=worker, args=(tid, ck, chat_url, wait_time)).start()
        st.success(f"ID: {tid}")

with col2:
    search = st.text_input("Enter ID").upper()
    if search and manager.get_task(search):
        data = manager.get_task(search)
        st.metric("Total Sent", data["count"])
        if data["last_screenshot"]:
            st.image(base64.b64decode(data["last_screenshot"]), caption="Ghost-Click View")
        st.code("\n".join(data["logs"][-15:]))
        if st.button("Stop"): data["stop"] = True
    
