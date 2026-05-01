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
st.set_page_config(page_title="FB ID Sniper Bot", layout="wide")

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
                try: self.tasks[tid]["last_screenshot"] = driver.get_screenshot_as_base_4()
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

def id_sniper_send(driver, tid, s_id):
    try:
        # 1. Popups clean karo taaki raasta saaf ho
        driver.execute_script("""
            document.querySelectorAll('div[role="dialog"], div[aria-label*="PIN"], div[aria-label*="restore"]').forEach(el => el.remove());
        """)

        # 2. Open Sticker Panel
        wait = WebDriverWait(driver, 12)
        icon_xpath = "//div[@aria-label='Choose a sticker'] | //i[contains(@style, 'stickers')]"
        icon = wait.until(EC.presence_of_element_located((By.XPATH, icon_xpath)))
        driver.execute_script("arguments[0].click();", icon)
        
        manager.update_log(tid, f"Panel opened. Sniping ID: {s_id}...", driver)
        time.sleep(8) # Loading & Decryption time

        # 3. ADVANCED ID TARGETING SCRIPT
        # Yeh script sticker ki ID dhoondh kar uspar 'Real Human' click simulate karegi
        sniper_script = f"""
        var targetId = "{s_id}";
        var foundEl = null;
        var imgs = document.querySelectorAll('img');
        
        for (var i = 0; i < imgs.length; i++) {{
            if (imgs[i].src.includes(targetId)) {{
                foundEl = imgs[i];
                break;
            }}
        }}

        if (foundEl) {{
            foundEl.scrollIntoView({{block: "center"}});
            var rect = foundEl.getBoundingClientRect();
            var x = rect.left + rect.width / 2;
            var y = rect.top + rect.height / 2;
            
            var events = ['mouseover', 'mousedown', 'click', 'mouseup'];
            events.forEach(type => {{
                var ev = new MouseEvent(type, {{
                    view: window, bubbles: true, cancelable: true,
                    clientX: x, clientY: y, buttons: 1
                }});
                foundEl.dispatchEvent(ev);
            }});
            return "HIT";
        }}
        return "MISS";
        """
        
        result = driver.execute_script(sniper_script)
        
        if result == "HIT":
            # Force Enter
            time.sleep(1)
            ActionChains(driver).send_keys(Keys.ENTER).perform()
            return True
        return False
    except Exception as e:
        manager.update_log(tid, "UI busy, retrying sniper sequence...")
        return False

def worker(tid, cookies, url, s_id, delay):
    driver = get_driver()
    try:
        driver.get("https://www.facebook.com")
        for c in cookies.split(';'):
            if '=' in c:
                n, v = c.strip().split('=', 1)
                driver.add_cookie({'name': n.strip(), 'value': v.strip(), 'domain': '.facebook.com'})
        
        driver.get(url)
        time.sleep(15)
        manager.tasks[tid]["status"] = "Running 🚀"

        while not manager.tasks[tid]["stop"]:
            if id_sniper_send(driver, tid, s_id):
                manager.tasks[tid]["count"] += 1
                manager.update_log(tid, f"🎯 SNIPED! Sticker ID {s_id} sent.")
            else:
                manager.update_log(tid, "ID not found in panel, refreshing...")
                driver.refresh()
                time.sleep(12)

            time.sleep(delay)
    finally:
        driver.quit()
        if tid in manager.tasks: manager.tasks[tid]["status"] = "Stopped"

# --- UI ---
st.title("🚀 FB E2EE Sticker ID Sniper")
col1, col2 = st.columns([1, 2])

with col1:
    ck = st.text_area("Cookies")
    chat_url = st.text_input("E2EE Chat Link")
    sticker_id = st.text_input("Enter Sticker ID (Numeric Only)")
    wait_time = st.slider("Delay (Sec)", 10, 300, 25)
    
    if st.button("🚀 Launch Sniper Bot"):
        if ck and chat_url and sticker_id:
            tid = manager.create_task()
            threading.Thread(target=worker, args=(tid, ck, chat_url, sticker_id, wait_time)).start()
            st.success(f"Sniper Task ID: {tid}")

with col2:
    search = st.text_input("Monitor ID").upper()
    if search and manager.get_task(search):
        data = manager.get_task(search)
        st.metric("Total Success", data["count"])
        if data["last_screenshot"]:
            st.image(base64.b64decode(data["last_screenshot"]), caption="Sniper View")
        st.code("\n".join(data["logs"][-15:]))
    
