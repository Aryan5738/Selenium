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
st.set_page_config(page_title="FB E2EE Special Bot", layout="wide")

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

def send_sticker_e2ee(driver, tid):
    try:
        wait = WebDriverWait(driver, 15)
        
        # 1. E2EE Special Sticker Icon Search
        # E2EE chats mein aria-label 'Choose a sticker' aksar nested hota hai
        manager.update_log(tid, "Searching for E2EE sticker icon...")
        
        icon_xpaths = [
            "//div[@aria-label='Choose a sticker']",
            "//div[@role='button']//i[contains(@style, 'stickers')]",
            "//div[contains(@aria-label, 'sticker')]"
        ]
        
        btn = None
        for path in icon_xpaths:
            try:
                btn = wait.until(EC.presence_of_element_located((By.XPATH, path)))
                if btn: break
            except: continue
            
        if btn:
            # Scroll and Click
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", btn)
            manager.update_log(tid, "E2EE Panel opened. Scanning stickers...", driver)
            
            time.sleep(7) # Encrypted panel takes longer to load

            # 2. Deep scan for sticker images
            # E2EE mein images ka structure alag hota hai
            stickers = driver.find_elements(By.CSS_SELECTOR, "div[role='gridcell'] img, div[aria-label='Stickers'] img, img[alt*='sticker']")
            
            if stickers:
                # Select a random one
                target = random.choice(stickers[:min(len(stickers), 12)])
                manager.update_log(tid, "Sticker found! Sending...", driver)
                
                # Double force click
                driver.execute_script("arguments[0].click();", target)
                time.sleep(1)
                # Confirm with Enter in case of E2EE confirmation
                ActionChains(driver).send_keys(Keys.ENTER).perform()
                return True
            else:
                manager.update_log(tid, "Panel empty or stickers hidden.", driver)
        return False
    except Exception as e:
        manager.update_log(tid, f"Interaction Error: {str(e)[:30]}", driver)
        return False

def worker(tid, cookies, e2ee_url, delay):
    driver = get_driver()
    try:
        manager.update_log(tid, "Logging in...")
        driver.get("https://www.facebook.com")
        for c in cookies.split(';'):
            if '=' in c:
                n, v = c.strip().split('=', 1)
                driver.add_cookie({'name': n.strip(), 'value': v.strip(), 'domain': '.facebook.com'})
        
        manager.update_log(tid, f"Opening E2EE Chat: {e2ee_url}")
        driver.get(e2ee_url)
        time.sleep(15) # Encrypted chats need more time to decrypt in browser
        
        manager.tasks[tid]["status"] = "Running ✅"
        while not manager.tasks[tid]["stop"]:
            if send_sticker_e2ee(driver, tid):
                manager.tasks[tid]["count"] += 1
                manager.update_log(tid, f"✅ Sticker #{manager.tasks[tid]['count']} sent.")
            else:
                manager.update_log(tid, "Failed to send. Refreshing session...")
                driver.refresh()
                time.sleep(12)
            
            time.sleep(delay + random.randint(2, 5))
            
    except Exception as e: manager.update_log(tid, f"Fatal: {e}")
    finally:
        driver.quit()
        manager.tasks[tid]["status"] = "Stopped"

# --- STREAMLIT UI ---
st.title("🛡️ FB E2EE Pro Sticker Bot")

col1, col2 = st.columns([1, 2])

with col1:
    st.info("E2EE Chat detected. Please ensure cookies are fresh.")
    ck = st.text_area("Cookies")
    # Yahan link auto-detect hoga aapke input se
    chat_link = st.text_input("E2EE Chat URL", placeholder="https://www.facebook.com/messages/e2ee/t/...")
    wait_time = st.number_input("Interval (Seconds)", 10, 300, 20)
    
    if st.button("🚀 Launch E2EE Bot", use_container_width=True):
        if ck and chat_link:
            tid = manager.create_task()
            threading.Thread(target=worker, args=(tid, ck, chat_link, wait_time)).start()
            st.success(f"Task Started! ID: {tid}")

with col2:
    search = st.text_input("Track Task ID").upper()
    if search:
        data = manager.get_task(search)
        if data:
            st.metric("Total Sent", data["count"])
            if data["last_screenshot"]:
                st.image(base64.b64decode(data["last_screenshot"]), caption="E2EE Live View", use_container_width=True)
            st.code("\n".join(data["logs"][-15:]))
            if st.button("Stop"): data["stop"] = True
        
