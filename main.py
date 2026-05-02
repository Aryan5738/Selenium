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
st.set_page_config(page_title="FB Ultra Sniper 2026", layout="wide")

class GlobalTaskManager:
    def __init__(self):
        self.tasks = {}

    def create_task(self):
        tid = str(uuid.uuid4())[:6].upper()
        self.tasks[tid] = {"status": "Initializing...", "logs": [], "count": 0, "stop": False, "last_screenshot": None}
        return tid

    def get_task(self, tid): return self.tasks.get(tid)

    def update_log(self, tid, msg, driver=None):
        if tid in self.tasks:
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            self.tasks[tid]["logs"].append(f"[{ts}] {msg}")
            if driver:
                try: self.tasks[tid]["last_screenshot"] = driver.get_screenshot_as_base64()
                except: pass

@st.cache_resource
def get_manager(): return GlobalTaskManager()

manager = get_manager()

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    # Anti-bot detection
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    service = Service(shutil.which("chromedriver") or "/usr/bin/chromedriver")
    return webdriver.Chrome(service=service, options=chrome_options)

def ultra_sniper_logic(driver, tid, s_id):
    try:
        # 1. Force Clean Popups (PIN, Restore, etc.)
        driver.execute_script("""
            var bad = ['div[role="dialog"]', 'div[aria-label*="PIN"]', 'div[aria-label*="restore"]'];
            bad.forEach(s => document.querySelectorAll(s).forEach(el => el.remove()));
        """)

        # 2. Open Sticker Panel
        wait = WebDriverWait(driver, 12)
        icon_xpath = "//div[@aria-label='Choose a sticker'] | //i[contains(@style, 'stickers')]"
        icon = wait.until(EC.presence_of_element_located((By.XPATH, icon_xpath)))
        driver.execute_script("arguments[0].click();", icon)
        
        manager.update_log(tid, f"Scanning Panel for ID: {s_id}...", driver)
        time.sleep(8) # Decryption wait

        # 3. DEEP SCAN & DISPATCH (Powerful JS)
        # Yeh script panel ke andar scroll karke ID dhoondhegi
        dispatch_script = f"""
        var targetId = "{s_id}";
        var found = false;
        
        // Function to find in all images
        function findAndClick() {{
            var imgs = document.querySelectorAll('img[src*="' + targetId + '"]');
            if (imgs.length > 0) {{
                var el = imgs[0];
                var rect = el.getBoundingClientRect();
                var ev = new MouseEvent('click', {{
                    view: window, bubbles: true, cancelable: true,
                    clientX: rect.left + rect.width/2, clientY: rect.top + rect.height/2
                }});
                el.dispatchEvent(ev);
                return true;
            }}
            return false;
        }}

        if (findAndClick()) return "HIT";

        // Agar nahi mila toh scroll karke dhoondho (Deep Scan)
        var grid = document.querySelector('div[role="grid"]');
        if (grid) {{
            grid.scrollTop = grid.scrollHeight / 2; // Middle scroll
            if (findAndClick()) return "HIT";
            grid.scrollTop = grid.scrollHeight; // Full scroll
            if (findAndClick()) return "HIT";
        }}
        return "MISS";
        """
        
        result = driver.execute_script(dispatch_script)
        
        if result == "HIT":
            time.sleep(1.5)
            # Enter key confirm
            driver.execute_script("window.dispatchEvent(new KeyboardEvent('keydown', {'key': 'Enter'}));")
            return True
        return False
    except:
        return False

def worker(tid, cookies, url, s_id, delay):
    while not manager.get_task(tid)["stop"]:
        driver = get_driver()
        try:
            driver.get("https://www.facebook.com")
            for c in cookies.split(';'):
                if '=' in c:
                    n, v = c.strip().split('=', 1)
                    driver.add_cookie({'name': n.strip(), 'value': v.strip(), 'domain': '.facebook.com'})
            
            driver.get(url)
            time.sleep(15)
            manager.tasks[tid]["status"] = "Sniper Active 🎯"
            
            local_loop = 0
            while not manager.tasks[tid]["stop"] and local_loop < 40:
                if ultra_sniper_logic(driver, tid, s_id):
                    manager.tasks[tid]["count"] += 1
                    local_loop += 1
                    manager.update_log(tid, f"💥 SNIPED! Sticker #{manager.tasks[tid]['count']}")
                else:
                    manager.update_log(tid, "ID not visible. Scrolling/Resetting...", driver)
                    driver.refresh()
                    time.sleep(12)
                time.sleep(delay)
            driver.quit()
        except:
            try: driver.quit()
            except: pass
            time.sleep(10)

# --- UI ---
st.title("🛡️ FB Ultra Sniper (Powerful ID-Mode)")
c1, c2 = st.columns([1, 2])

with c1:
    ck = st.text_area("Cookies")
    target = st.text_input("Target Chat Link")
    sticker_id = st.text_input("Enter Powerful Sticker ID", placeholder="e.g. 212480906326769")
    spd = st.number_input("Delay (Sec)", 10, 600, 25)
    
    if st.button("🚀 Launch Ultra Sniper"):
        if ck and target and sticker_id:
            tid = manager.create_task()
            threading.Thread(target=worker, args=(tid, ck, target, sticker_id, spd)).start()
            st.success(f"Bot Started! ID: {tid}")

with c2:
    search = st.text_input("Monitor ID").upper()
    if search:
        data = manager.get_task(search)
        if data:
            st.metric("Total Success", data["count"])
            if data["last_screenshot"]:
                st.image(base64.b64decode(data["last_screenshot"]), use_container_width=True)
            st.code("\n".join(data["logs"][-15:]))
            if st.button("Stop"): data["stop"] = True
      
