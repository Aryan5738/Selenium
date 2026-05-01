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
st.set_page_config(page_title="FB E2EE Anti-Popup Pro", layout="wide")

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
    chrome_options.add_argument("--window-size=1600,900")
    service = Service(shutil.which("chromedriver") or "/usr/bin/chromedriver")
    return webdriver.Chrome(service=service, options=chrome_options)

# --- UPDATED: POPUP & CONFIRMATION CRUSHER ---
def handle_blocking_popups(driver, tid):
    try:
        # 1. PIN Popup Close
        pin_close = driver.find_elements(By.XPATH, "//div[@role='dialog']//div[@aria-label='Close']")
        
        # 2. "Don't restore messages" Button (Aapke screenshot ka solution)
        restore_confirm = driver.find_elements(By.XPATH, "//span[contains(text(), 'Don\'t restore')] | //div[@role='button'][descendant::span[contains(text(), 'restore')]]")
        
        found_any = False
        
        # Confirmation button par click karein
        for btn in restore_confirm:
            if btn.is_displayed():
                manager.update_log(tid, "🎯 Clicking 'Don't restore messages'...", driver)
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(3)
                found_any = True
        
        # Agar wo na ho toh normal close button dhoondhein
        if not found_any:
            for btn in pin_close:
                if btn.is_displayed():
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(2)
                    found_any = True
                    
        return found_any
    except:
        return False

def send_sticker_force(driver, tid):
    try:
        wait = WebDriverWait(driver, 15)
        
        # Popups ko clean karein
        handle_blocking_popups(driver, tid)
        
        # 1. Sticker Icon dhoondhein
        icon_xpath = "//div[@aria-label='Choose a sticker'] | //div[@role='button']//i[contains(@style, 'stickers')]"
        sticker_btn = wait.until(EC.presence_of_element_located((By.XPATH, icon_xpath)))
        
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", sticker_btn)
        time.sleep(1)
        driver.execute_script("arguments[0].click();", sticker_btn)
        
        manager.update_log(tid, "Sticker panel opened. Scanning...", driver)
        time.sleep(7) 

        # 2. Stickers grid scan
        stickers = driver.find_elements(By.CSS_SELECTOR, "div[role='gridcell'] img, div[aria-label='Stickers'] img, img[alt*='sticker']")
        
        if stickers:
            target = random.choice(stickers[:min(len(stickers), 15)])
            driver.execute_script("arguments[0].click();", target)
            time.sleep(1)
            ActionChains(driver).send_keys(Keys.ENTER).perform()
            return True
        else:
            manager.update_log(tid, "Panel loaded but no stickers. Refreshing...", driver)
            return False
    except Exception as e:
        manager.update_log(tid, f"Status: Waiting for UI...", driver)
        return False

def background_worker(tid, cookie_str, url, delay):
    driver = get_driver()
    try:
        driver.get("https://www.facebook.com")
        for c in cookie_str.split(';'):
            if '=' in c:
                name, val = c.strip().split('=', 1)
                driver.add_cookie({'name': name.strip(), 'value': val.strip(), 'domain': '.facebook.com'})
        
        driver.get(url)
        time.sleep(15) 
        
        # Initial popup cleaning
        handle_blocking_popups(driver, tid)
        
        manager.tasks[tid]["status"] = "Running ✅"

        while not manager.tasks[tid]["stop"]:
            success = send_sticker_force(driver, tid)
            if success:
                manager.tasks[tid]["count"] += 1
                manager.update_log(tid, f"✅ Sticker #{manager.tasks[tid]['count']} sent.")
            else:
                driver.refresh()
                time.sleep(12)
                handle_blocking_popups(driver, tid)

            time.sleep(delay + random.randint(3, 8))
    except Exception as e:
        manager.update_log(tid, f"Fatal: {str(e)}")
    finally:
        driver.quit()
        if tid in manager.tasks: manager.tasks[tid]["status"] = "Stopped"

# --- UI ---
st.title("🛡️ FB E2EE Pro (Don't Restore Fix)")
c1, c2 = st.columns([1, 2])

with c1:
    ck = st.text_area("Cookies")
    chat_url = st.text_input("E2EE Chat Link")
    wait_time = st.slider("Interval (Sec)", 10, 300, 25)
    if st.button("🚀 Start Bot"):
        tid = manager.create_task()
        threading.Thread(target=background_worker, args=(tid, ck, chat_url, wait_time)).start()
        st.success(f"Task ID: {tid}")

with c2:
    search = st.text_input("Monitor ID").upper()
    if search:
        data = manager.get_task(search)
        if data:
            st.metric("Total Sent", data["count"])
            if data["last_screenshot"]:
                st.image(base64.b64decode(data["last_screenshot"]), caption="E2EE Live View")
            st.code("\n".join(data["logs"][-15:]))
            if st.button("Stop"): data["stop"] = True
            
