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
st.set_page_config(page_title="FB E2EE God Mode", layout="wide")

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

def clean_ui(driver, tid):
    """Sabh faltu popups ko saaf karne ke liye"""
    popups = [
        "//div[@role='dialog']//div[@aria-label='Close']",
        "//span[contains(text(), 'restore')]",
        "//div[@aria-label='Don’t restore messages']",
        "//div[@role='button']//span[text()='Cancel']"
    ]
    for p in popups:
        try:
            btns = driver.find_elements(By.XPATH, p)
            for b in btns:
                if b.is_displayed():
                    driver.execute_script("arguments[0].click();", b)
                    time.sleep(1)
        except: pass

def send_sticker_god_mode(driver, tid):
    try:
        wait = WebDriverWait(driver, 10)
        clean_ui(driver, tid)

        # 1. Sticker Icon Click
        icon_xpath = "//div[@aria-label='Choose a sticker'] | //div[@role='button']//i[contains(@style, 'stickers')]"
        sticker_btn = wait.until(EC.presence_of_element_located((By.XPATH, icon_xpath)))
        driver.execute_script("arguments[0].click();", sticker_btn)
        
        manager.update_log(tid, "Sticker panel opened.", driver)
        time.sleep(5) 

        # 2. Hardcore Sticker Selection
        # Hum generic selectors use karenge jo har sticker pack pe kaam karein
        stickers = driver.find_elements(By.CSS_SELECTOR, "div[role='gridcell'] img, img[src*='fbcdn'], img[alt*='sticker']")
        
        if stickers:
            # Kisi bhi random sticker ko target karo
            target = random.choice(stickers[:min(len(stickers), 10)])
            manager.update_log(tid, "Sticker found! Forcing click sequence...", driver)
            
            # METHOD A: JS Click
            driver.execute_script("arguments[0].click();", target)
            time.sleep(0.5)
            
            # METHOD B: Action Chains (Hover and Click)
            actions = ActionChains(driver)
            actions.move_to_element(target).click().perform()
            time.sleep(0.5)
            
            # METHOD C: Force Enter Key
            actions.send_keys(Keys.ENTER).perform()
            
            manager.update_log(tid, "Click sequence finished.", driver)
            return True
        return False
    except Exception as e:
        manager.update_log(tid, "UI interaction failed. Retrying...", driver)
        return False

def worker(tid, cookies, url, delay):
    driver = get_driver()
    try:
        driver.get("https://www.facebook.com")
        for c in cookies.split(';'):
            if '=' in c:
                n, v = c.strip().split('=', 1)
                driver.add_cookie({'name': n.strip(), 'value': v.strip(), 'domain': '.facebook.com'})
        
        driver.get(url)
        time.sleep(12)
        manager.tasks[tid]["status"] = "Running ✅"

        while not manager.tasks[tid]["stop"]:
            if send_sticker_god_mode(driver, tid):
                manager.tasks[tid]["count"] += 1
                manager.update_log(tid, f"✅ Sticker #{manager.tasks[tid]['count']} sent!")
            else:
                driver.refresh()
                time.sleep(10)
            
            time.sleep(delay + random.randint(2, 4))
    finally:
        driver.quit()
        if tid in manager.tasks: manager.tasks[tid]["status"] = "Stopped"

# --- UI ---
st.title("🚀 FB E2EE God-Mode Sticker Bot")
c1, c2 = st.columns([1, 2])

with c1:
    ck = st.text_area("Cookies")
    chat_url = st.text_input("E2EE Chat Link")
    wait_time = st.slider("Wait Time (Sec)", 5, 300, 15)
    if st.button("🚀 Start God-Mode Bot"):
        tid = manager.create_task()
        threading.Thread(target=worker, args=(tid, ck, chat_url, wait_time)).start()
        st.success(f"Task ID: {tid}")

with c2:
    search = st.text_input("Monitor Task ID").upper()
    if search:
        data = manager.get_task(search)
        if data:
            st.metric("Total Sent", data["count"])
            if data["last_screenshot"]:
                st.image(base64.b64decode(data["last_screenshot"]), caption="Live Browser Screen")
            st.code("\n".join(data["logs"][-15:]))
            if st.button("Stop"): data["stop"] = True
        
