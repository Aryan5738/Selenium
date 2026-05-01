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
st.set_page_config(page_title="FB Force Sticker Pro", layout="wide")

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
    # Mobile User Agent for better stability
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36")
    service = Service(shutil.which("chromedriver") or "/usr/bin/chromedriver")
    return webdriver.Chrome(service=service, options=chrome_options)

def send_sticker_mobile(driver, tid):
    try:
        wait = WebDriverWait(driver, 15)
        
        # 1. Look for Sticker Icon in Mobile View
        # Mobile Messenger (m.facebook.com) uses different classes
        manager.update_log(tid, "Searching for sticker icon...")
        icon_selectors = [
            "//div[@aria-label='Stickers']",
            "//div[@aria-label='Choose a sticker']",
            "//i[contains(@class, 'sticker')]",
            "//div[@role='button' and contains(@aria-label, 'Sticker')]"
        ]
        
        btn = None
        for s in icon_selectors:
            try:
                btn = wait.until(EC.element_to_be_clickable((By.XPATH, s)))
                if btn: break
            except: continue
            
        if btn:
            driver.execute_script("arguments[0].click();", btn)
            manager.update_log(tid, "Panel Opened. Selecting sticker...", driver)
            time.sleep(5) 

            # 2. Select first visible sticker
            stickers = driver.find_elements(By.CSS_SELECTOR, "div[role='gridcell'] img, img[src*='sticker']")
            
            if stickers:
                target = random.choice(stickers[:min(len(stickers), 15)])
                driver.execute_script("arguments[0].click();", target)
                return True
            else:
                manager.update_log(tid, "No stickers found in panel.", driver)
        return False
    except Exception as e:
        manager.update_log(tid, f"Error: {str(e)[:30]}", driver)
        return False

def worker(tid, cookies, target, delay):
    driver = get_driver()
    try:
        # Pre-Login
        driver.get("https://m.facebook.com")
        for c in cookies.split(';'):
            if '=' in c:
                n, v = c.strip().split('=', 1)
                driver.add_cookie({'name': n.strip(), 'value': v.strip(), 'domain': '.facebook.com'})
        
        # Determine Mobile Chat URL
        # Mobile view chat link pattern
        if target.isdigit():
            chat_url = f"https://m.facebook.com/messages/read/?tid=cid.c.{target}%3A{target}"
        else:
            # Fallback to general messenger
            chat_url = f"https://www.facebook.com/messages/t/{target}"
            
        manager.update_log(tid, f"Navigating to: {chat_url}")
        driver.get(chat_url)
        time.sleep(10)
        
        manager.tasks[tid]["status"] = "Running ✅"
        while not manager.tasks[tid]["stop"]:
            if send_sticker_mobile(driver, tid):
                manager.tasks[tid]["count"] += 1
                manager.update_log(tid, f"✅ Done! Sent #{manager.tasks[tid]['count']}", driver)
            else:
                manager.update_log(tid, "Sticker failed. Refreshing...", driver)
                driver.refresh()
                time.sleep(10)
            
            time.sleep(delay)
    except Exception as e: manager.update_log(tid, f"Fatal: {e}")
    finally:
        driver.quit()
        manager.tasks[tid]["status"] = "Stopped"

# --- UI ---
st.title("🔥 FB Ultra Pro Sticker Bot")

tab_l, tab_r = st.tabs(["🚀 Setup", "📊 Status"])

with tab_l:
    ck = st.text_area("Cookies (c_user=...; xs=...;)")
    target_id = st.text_input("User UID / Username")
    speed = st.number_input("Delay", 10, 300, 20)
    if st.button("Launch Bot"):
        tid = manager.create_task()
        threading.Thread(target=worker, args=(tid, ck, target_id, speed)).start()
        st.success(f"Started! ID: {tid}")

with tab_r:
    search = st.text_input("Monitor ID").upper()
    if search:
        data = manager.get_task(search)
        if data:
            col1, col2 = st.columns(2)
            col1.metric("Stickers Sent", data["count"])
            col2.metric("Status", data["status"])
            
            if data["last_screenshot"]:
                st.subheader("📸 Browser Live Preview")
                st.image(base64.b64decode(data["last_screenshot"]), use_container_width=True)
            
            with st.expander("Logs"):
                st.code("\n".join(data["logs"][-15:]))
            if st.button("Stop"): data["stop"] = True
        
