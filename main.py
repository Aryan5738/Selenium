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

# --- CONFIG ---
st.set_page_config(page_title="24/7 Shiba Sniper", layout="wide")

@st.cache_resource
class GlobalTaskManager:
    def __init__(self):
        self.tasks = {}

    def create_task(self):
        tid = str(uuid.uuid4())[:6].upper()
        self.tasks[tid] = {"status": "Starting...", "logs": [], "count": 0, "stop": False, "last_screenshot": None}
        return tid

    def update_log(self, tid, msg, driver=None):
        if tid in self.tasks:
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            self.tasks[tid]["logs"].append(f"[{ts}] {msg}")
            if driver:
                try: self.tasks[tid]["last_screenshot"] = driver.get_screenshot_as_base64()
                except: pass

manager = GlobalTaskManager()
SHIBA_IDS = ["212482136326646", "219662825608577", "212483102993216", "1747083982269520", "219665422274984"]

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    service = Service(shutil.which("chromedriver") or "/usr/bin/chromedriver")
    return webdriver.Chrome(service=service, options=chrome_options)

def never_stop_logic(driver, tid, s_id):
    try:
        # Force Clean Popups every time
        driver.execute_script("""
            var bad = ['div[role="dialog"]', 'div[aria-label*="PIN"]', 'div[aria-label*="restore"]', '.layerCancel'];
            bad.forEach(s => document.querySelectorAll(s).forEach(el => el.remove()));
        """)

        # Open Panel
        wait = WebDriverWait(driver, 12)
        icon_xpath = "//div[@aria-label='Choose a sticker'] | //i[contains(@style, 'stickers')]"
        icon = wait.until(EC.presence_of_element_located((By.XPATH, icon_xpath)))
        driver.execute_script("arguments[0].click();", icon)
        
        time.sleep(8) # Loading stickers

        # Native Injection Click
        inject = f"""
        var id = "{s_id}";
        var el = document.querySelector('img[src*="' + id + '"]');
        if (el) {{
            var r = el.getBoundingClientRect();
            var e = new MouseEvent('click', {{view:window, bubbles:true, clientX:r.left+r.width/2, clientY:r.top+r.height/2}});
            el.dispatchEvent(e);
            return true;
        }}
        return false;
        """
        if driver.execute_script(inject):
            time.sleep(1)
            driver.execute_script("window.dispatchEvent(new KeyboardEvent('keydown', {'key': 'Enter'}));")
            return True
        return False
    except:
        return False

def worker(tid, cookies, url, delay):
    while not manager.tasks[tid]["stop"]: # Infinite Loop Start
        driver = get_driver()
        try:
            manager.update_log(tid, "Initializing New Session...")
            driver.get("https://www.facebook.com")
            for c in cookies.split(';'):
                if '=' in c:
                    n, v = c.strip().split('=', 1)
                    driver.add_cookie({'name': n.strip(), 'value': v.strip(), 'domain': '.facebook.com'})
            
            driver.get(url)
            time.sleep(15)
            
            manager.tasks[tid]["status"] = "Running 24/7 🛡️"
            
            local_count = 0
            while not manager.tasks[tid]["stop"] and local_count < 50:
                # Security Check: Are we still on the chat page?
                if "messages" not in driver.current_url:
                    driver.get(url)
                    time.sleep(10)

                current_sid = random.choice(SHIBA_IDS)
                if never_stop_logic(driver, tid, current_sid):
                    manager.tasks[tid]["count"] += 1
                    local_count += 1
                    manager.update_log(tid, f"✅ Sent Sticker #{manager.tasks[tid]['count']}", driver)
                else:
                    manager.update_log(tid, "Sticker Panel stuck. Resetting UI...", driver)
                    driver.refresh()
                    time.sleep(12)
                
                time.sleep(delay)
            
            manager.update_log(tid, "Refreshing browser to clear memory...")
            driver.quit() # Session restart for stability

        except Exception as e:
            manager.update_log(tid, f"Error encountered: {str(e)[:30]}. Rebooting...")
            try: driver.quit()
            except: pass
            time.sleep(10)

# --- UI ---
st.title("🛡️ 24/7 Shiba Sniper (Never-Stop Edition)")
c1, c2 = st.columns([1, 2])

with c1:
    st.info("UptimeRobot use karein is app ko 24/7 zinda rakhne ke liye.")
    ck = st.text_area("Fresh Cookies")
    target = st.text_input("Target Chat URL")
    spd = st.number_input("Interval (Seconds)", 10, 600, 25)
    if st.button("🚀 Start Non-Stop Bot"):
        tid = manager.create_task()
        threading.Thread(target=worker, args=(tid, ck, target, spd)).start()
        st.success(f"Bot started! Task ID: {tid}")

with c2:
    search = st.text_input("Monitor Task ID").upper()
    if search and manager.get_task(search):
        data = manager.get_task(search)
        st.metric("Total Stickers Sent", data["count"])
        if data["last_screenshot"]:
            st.image(base64.b64decode(data["last_screenshot"]), use_container_width=True)
        st.code("\n".join(data["logs"][-15:]))
        if st.button("Stop Bot"): data["stop"] = True
