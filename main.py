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
st.set_page_config(page_title="FB Direct Sticker", layout="wide")

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
    chrome_options.add_argument("--window-size=1280,800")
    service = Service(shutil.which("chromedriver") or "/usr/bin/chromedriver")
    return webdriver.Chrome(service=service, options=chrome_options)

def send_sticker_direct(driver, tid):
    try:
        wait = WebDriverWait(driver, 10)
        
        # 1. Open Sticker Panel
        # Optimized selectors for Direct Messenger
        selectors = [
            "//div[@aria-label='Choose a sticker']",
            "//div[@aria-label='Stickers']",
            "//span[contains(@class, 'x10l6tqk')]//div[@role='button']"
        ]
        
        btn = None
        for s in selectors:
            try:
                btn = wait.until(EC.element_to_be_clickable((By.XPATH, s)))
                if btn: break
            except: continue
            
        if btn:
            driver.execute_script("arguments[0].click();", btn)
            manager.update_log(tid, "Sticker panel clicked. Waiting 5s...", driver)
            time.sleep(5) 

            # 2. Hard-Search for any sticker image
            # Messenger stickers use 'img' tags with specific classes or parents
            stickers = driver.find_elements(By.CSS_SELECTOR, "div[role='gridcell'] img, img[alt*='sticker'], div[aria-label='Stickers'] img")
            
            if stickers:
                target = random.choice(stickers[:min(len(stickers), 12)])
                manager.update_log(tid, "Sticker found! Clicking...", driver)
                
                # Double click approach
                driver.execute_script("arguments[0].click();", target)
                time.sleep(0.5)
                ActionChains(driver).send_keys(Keys.ENTER).perform()
                return True
            else:
                manager.update_log(tid, "Panel opened but stickers didn't load.", driver)
        else:
            manager.update_log(tid, "Sticker button not found.", driver)
        return False
    except Exception as e:
        manager.update_log(tid, f"Error: {str(e)[:30]}", driver)
        return False

def worker(tid, cookies, target, delay):
    driver = get_driver()
    try:
        # Pre-Login
        driver.get("https://www.facebook.com")
        for c in cookies.split(';'):
            if '=' in c:
                n, v = c.strip().split('=', 1)
                driver.add_cookie({'name': n, 'value': v, 'domain': '.facebook.com'})
        
        # Determine URL: Sidha Messenger
        if target.isdigit():
            chat_url = f"https://www.facebook.com/messages/t/{target}"
        else:
            # Username fallback - hum koshish karenge ki ye messenger par hi redirect ho
            chat_url = f"https://www.facebook.com/messages/t/{target}"
            
        manager.update_log(tid, f"Navigating to Messenger: {chat_url}")
        driver.get(chat_url)
        time.sleep(10)
        
        manager.tasks[tid]["status"] = "Running ✅"
        while not manager.tasks[tid]["stop"]:
            if send_sticker_direct(driver, tid):
                manager.tasks[tid]["count"] += 1
                manager.update_log(tid, f"✅ Sticker #{manager.tasks[tid]['count']} sent.")
            else:
                manager.update_log(tid, "Retrying...")
                driver.refresh()
                time.sleep(8)
            
            time.sleep(delay)
    except Exception as e: manager.update_log(tid, f"Fatal: {e}")
    finally:
        driver.quit()
        manager.tasks[tid]["status"] = "Stopped"

# --- STREAMLIT UI ---
st.title("⚡ FB Direct Messenger Bot")
c1, c2 = st.columns([1, 2])

with c1:
    ck = st.text_area("Cookies")
    target_id = st.text_input("User ID or Username", placeholder="1000... or nataliya.lalain")
    wait_time = st.number_input("Interval (Seconds)", 10, 300, 20)
    if st.button("Start Sending"):
        tid = manager.create_task()
        threading.Thread(target=worker, args=(tid, ck, target_id, wait_time)).start()
        st.success(f"Task ID: {tid}")

with c2:
    search = st.text_input("Monitor ID").upper()
    if search:
        data = manager.get_task(search)
        if data:
            st.metric("Sent", data["count"])
            if data["last_screenshot"]:
                st.image(base64.b64decode(data["last_screenshot"]), caption="Direct Messenger View")
            st.code("\n".join(data["logs"][-10:]))
            if st.button("Stop"): data["stop"] = True
