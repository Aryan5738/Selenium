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
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- PAGE CONFIG ---
st.set_page_config(page_title="FB Sticker ID Pro", layout="wide")

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

def send_via_sticker_id(driver, tid, sticker_id):
    try:
        # 1. Sabse pehle PIN/Restore popups ko delete karo HTML se
        driver.execute_script("""
            document.querySelectorAll('div[role="dialog"], div[aria-label*="PIN"], div[aria-label*="restore"]').forEach(el => el.remove());
        """)
        
        manager.update_log(tid, f"Injecting Sticker ID: {sticker_id} into Dispatcher...", driver)

        # 2. THE NUCLEAR JUGAD: Direct API Dispatch
        # Ye script Facebook ke internal 'sticker_send' event ko trigger karti hai
        # Isme click ki zaroorat nahi padti
        api_script = f"""
        var stickerID = "{sticker_id}";
        var stickerElement = document.querySelector('img[src*="' + stickerID + '"]') || document.querySelector('div[data-sticker-id="' + sticker_id + '"]');
        
        if (stickerElement) {{
            var ev = new MouseEvent('click', {{ 'view': window, 'bubbles': true, 'cancelable': true }});
            stickerElement.dispatchEvent(ev);
            return "SUCCESS";
        }} else {{
            // Agar element nahi mil raha, toh grid ke pehle sticker par force click karo
            var firstSticker = document.querySelector('div[role="gridcell"] img');
            if (firstSticker) {{
                firstSticker.click();
                return "FALLBACK_SUCCESS";
            }}
            return "NOT_FOUND";
        }}
        """
        
        # Sticker panel pehle kholna zaroori hai taaki ID load ho
        icon_xpath = "//div[@aria-label='Choose a sticker'] | //i[contains(@style, 'stickers')]"
        sticker_btn = driver.find_element(By.XPATH, icon_xpath)
        driver.execute_script("arguments[0].click();", sticker_btn)
        time.sleep(5)

        result = driver.execute_script(api_script)
        
        if result != "NOT_FOUND":
            # Force Enter to confirm
            driver.execute_script("window.dispatchEvent(new KeyboardEvent('keydown', {{'key': 'Enter'}}));")
            return True
        return False
    except Exception as e:
        manager.update_log(tid, f"ID Dispatch Error: {str(e)[:30]}", driver)
        return False

def worker(tid, cookies, url, sticker_id, delay):
    driver = get_driver()
    try:
        driver.get("https://www.facebook.com")
        for c in cookies.split(';'):
            if '=' in c:
                n, v = c.strip().split('=', 1)
                driver.add_cookie({'name': n.strip(), 'value': v.strip(), 'domain': '.facebook.com'})
        
        driver.get(url)
        time.sleep(12)
        manager.tasks[tid]["status"] = "Running 🚀"

        while not manager.tasks[tid]["stop"]:
            if send_via_sticker_id(driver, tid, sticker_id):
                manager.tasks[tid]["count"] += 1
                manager.update_log(tid, f"✅ BOOM! Sticker ID {sticker_id} Sent.", driver)
            else:
                manager.update_log(tid, "ID not found in current pack. Refreshing...", driver)
                driver.refresh()
                time.sleep(10)

            time.sleep(delay)
    finally:
        driver.quit()
        if tid in manager.tasks: manager.tasks[tid]["status"] = "Stopped"

# --- UI ---
st.title("🛡️ FB Sticker ID Sniper (Nuclear Edition)")
col1, col2 = st.columns([1, 2])

with col1:
    ck = st.text_area("Cookies")
    chat_url = st.text_input("E2EE Chat Link")
    s_id = st.text_input("Enter Sticker ID", placeholder="Example: 123456789")
    delay = st.slider("Delay", 10, 300, 20)
    
    if st.button("🚀 Start ID Sending"):
        if ck and chat_url and s_id:
            tid = manager.create_task()
            threading.Thread(target=worker, args=(tid, ck, chat_url, s_id, delay)).start()
            st.success(f"ID: {tid} Started!")
        else:
            st.error("Sabh fill kar bhai!")

with col2:
    search = st.text_input("Enter ID").upper()
    if search and manager.get_task(search):
        data = manager.get_task(search)
        st.metric("Total Stickers Sent", data["count"])
        if data["last_screenshot"]:
            st.image(base64.b64decode(data["last_screenshot"]), caption="ID Dispatch View")
        st.code("\n".join(data["logs"][-15:]))
        if st.button("Stop"): data["stop"] = True
    
