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
st.set_page_config(page_title="FB E2EE Popup Crusher", layout="wide")

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

# --- NEW: POPUP BYPASS FUNCTION ---
def handle_blocking_popups(driver, tid):
    try:
        # 1. Close 'Restore chats' popup (image_6.png issue)
        # Selectors target the common close buttons for that specific PIN popup
        popup_close_selectors = [
            "//div[@role='dialog'][contains(., 'Enter your PIN')]//div[@aria-label='Close']",
            "//div[@role='dialog'][contains(., 'PIN')]//i",
            "//div[@aria-label='Close' and @role='button']"
        ]
        
        for xpath in popup_close_selectors:
            close_btns = driver.find_elements(By.XPATH, xpath)
            for btn in close_btns:
                if btn.is_displayed():
                    manager.update_log(tid, "🚨 Blocking popup detected. Forcing close...", driver)
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(2)
                    return True # Found and closed
        return False
    except:
        return False

def send_sticker_force(driver, tid):
    try:
        wait = WebDriverWait(driver, 15)
        
        # --- NEW: CRUSH POPUPS FIRST ---
        handle_blocking_popups(driver, tid)
        
        # 1. Click Sticker Icon
        manager.update_log(tid, "Searching for sticker icon...")
        icon_xpath = (
            "//div[@aria-label='Choose a sticker'] | "
            "//div[@role='button']//i[contains(@style, 'stickers')]"
        )
        
        sticker_btn = wait.until(EC.presence_of_element_located((By.XPATH, icon_xpath)))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", sticker_btn)
        time.sleep(1)
        driver.execute_script("arguments[0].click();", sticker_btn)
        
        manager.update_log(tid, "Panel opened. Scanning grid...", driver)
        time.sleep(7) 

        # 2. Deep scan for any sticker images (E2EE Grid)
        stickers = driver.find_elements(By.CSS_SELECTOR, "div[role='gridcell'] img, div[aria-label='Stickers'] img, img[alt*='sticker']")
        
        if stickers:
            target = random.choice(stickers[:min(len(stickers), 15)])
            manager.update_log(tid, f"Found {len(stickers)} stickers. Clicking one...", driver)
            
            # Click the sticker
            driver.execute_script("arguments[0].click();", target)
            time.sleep(1)
            # Confirm sending with Enter
            ActionChains(driver).send_keys(Keys.ENTER).perform()
            return True
        else:
            manager.update_log(tid, "Grid empty or still blocked. Forcing refresh...", driver)
        return False
    except Exception as e:
        manager.update_log(tid, f"Error: {str(e)[:40]}", driver)
        # Extra safety: refresh page on error to clean popups
        return False

def background_worker(tid, cookie_str, url, delay):
    driver = get_driver()
    if not driver: return

    try:
        driver.get("https://www.facebook.com")
        for c in cookie_str.split(';'):
            if '=' in c:
                name, val = c.strip().split('=', 1)
                driver.add_cookie({'name': name.strip(), 'value': val.strip(), 'domain': '.facebook.com'})
        
        manager.update_log(tid, f"Navigating to E2EE Chat...")
        driver.get(url)
        time.sleep(15) # Wait for decryption and first popups
        
        # --- NEW: CRUSH POPUPS ON INITIAL LOAD ---
        handle_blocking_popups(driver, tid)
        time.sleep(2)

        manager.tasks[tid]["status"] = "Running ✅"

        while not manager.tasks[tid]["stop"]:
            success = send_sticker_force(driver, tid)
            if success:
                manager.tasks[tid]["count"] += 1
                manager.update_log(tid, f"✅ Done! Total: {manager.tasks[tid]['count']}")
            else:
                manager.update_log(tid, "Page refresh triggered.")
                driver.refresh()
                time.sleep(12) # Long wait after refresh

            time.sleep(delay + random.randint(3, 8))

    except Exception as e:
        manager.update_log(tid, f"Fatal: {str(e)}")
    finally:
        driver.quit()
        if tid in manager.tasks: manager.tasks[tid]["status"] = "Stopped"

# --- UI ---
st.title("🛡️ FB E2EE Popup Crusher & Sticker Bot")
c1, c2 = st.columns([1, 2])

with c1:
    ck = st.text_area("Cookies")
    chat_url = st.text_input("E2EE Chat Link")
    wait_time = st.slider("Delay", 10, 300, 25)
    
    if st.button("🚀 Start Crusher Bot"):
        tid = manager.create_task()
        threading.Thread(target=background_worker, args=(tid, ck, chat_url, wait_time)).start()
        st.success(f"ID: {tid}")

with c2:
    search = st.text_input("Monitor ID").upper()
    if search:
        data = manager.get_task(search)
        if data:
            col_a, col_b = st.columns(2)
            col_a.metric("Total Sent", data["count"])
            col_b.metric("Status", data["status"])
            if data["last_screenshot"]:
                st.image(base64.b64decode(data["last_screenshot"]), caption="E2EE Live Preview (PIN popup should be closed)", use_container_width=True)
            st.code("\n".join(data["logs"][-12:]))
            if st.button("Stop"): data["stop"] = True
