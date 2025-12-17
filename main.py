import os
import time
import shutil
import streamlit as st  # Fixed: Added missing import
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

# --- PAGE CONFIG ---
# This must be the very first Streamlit command
st.set_page_config(page_title="FB Auto Sender", layout="centered")
st.title("FB Sender (Force Send 🚀)")

# --- LIVE LOGGER ---
log_placeholder = st.empty()

def log(message, level="info"):
    """Live Logging Function"""
    if level == "info":
        log_placeholder.info(f"ℹ️ {message}")
    elif level == "success":
        log_placeholder.success(f"✅ {message}")
    elif level == "error":
        log_placeholder.error(f"❌ {message}")
    elif level == "warn":
        log_placeholder.warning(f"⚠️ {message}")
    print(f"LOG: {message}")

# --- USER INPUTS ---
st.subheader("1. Login Details")
DEFAULT_COOKIE = "Sb=x-4VZxbqkmCAawFwsNZch1cr; m_pixel_ratio=2; ps_l=1; ps_n=1; usida=eyJ2ZXIiOjEsImlkIjoiQXNwa3poZzFqMWYwbmsiLCJ0aW1lIjoxNzM2MDIyNjM2fQ%3D%3D; oo=v1; vpd=v1%3B634x360x2; x-referer=eyJyIjoiL2NoZWNrcG9pbnQvMTUwMTA5MjgyMzUyNTI4Mi9sb2dvdXQvP25leHQ9aHR0cHMlM0ElMkYlMkZtLmZhY2Vib29rLmNvbSUyRiIsImgiOiIvY2hlY2twb2ludC8xNTAxMDkyODIzNTI1MjgyL2xvZ291dC8%2FbmV4dD1odHRwcyUzQSUyRiUyRm0uZmFjZWJvb2suY29tJTJGIiwicyI6Im0ifQ%3D%3D; pas=100018459948597%3AyY8iKAz4qS%2C61576915895165%3Ah3M07gRmIr%2C100051495735634%3AaWZGIhmpcN%2C100079959253161%3AERjtJDwIKY%2C100085135237853%3ASJzxBm80J0%2C100039111611241%3AYdPtkzDOqQ%2C61551133266466%3Aw3egO2jjPR%2C61580506865263%3AgBocX6ACyH%2C61580725287646%3Az32vfC8XFx%2C61580627947722%3NGvvqUwSjM%2C61580696818474%3AOANvC0tEZ7; locale=en_GB; c_user=61580506865263; datr=g8olaZiZYQMO7uPOZr9LIPht; xs=13%3AQoLIRrRzRReDAA%3A2%3A1764084356%3A-1%3A-1; wl_cbv=v2%3Bclient_version%3A2985%3Btimestamp%3A1764084357; fbl_st=100727294%3BT%3A29401406; fr=1DU5Jl03wP4b7GP8t.AWefU_KjBG8Z5AZgumwZsBRycYqwUkK410GOJ9ACH6HquX9_4fk.BoxuDH..AAA.0.0.BpJcqK.AWdFN0M6cD-SLsdpO8kcmDP_8_s; presence=C%7B%22lm3%22%3A%22sc.800019873203125%22%2C%22t3%22%3A%5B%7B%22o%22%3A0%2C%22i%22%3A%22g.1160300088952219%22%7D%5D%2C%22utc3%22%3A1764084412300%2C%22v%22%3A1%7D; wd=1280x2254; dpr=2"

cookie_input = st.text_area("Cookie String", value=DEFAULT_COOKIE, height=100)
user_pin = st.text_input("Enter 6-Digit PIN (Optional)", max_chars=6, type="password")

st.subheader("2. Message Details")
target_url = st.text_input("Chat URL", value="https://www.facebook.com/messages/e2ee/t/61558458805222")
message_text = st.text_input("Message", value="Hello from Bot!")

col1, col2 = st.columns(2)
with col1:
    enable_infinite = st.checkbox("Enable Infinite Mode", value=False)
with col2:
    delay_time = st.number_input("Delay (Seconds)", min_value=1, value=2)

def parse_cookies(cookie_string):
    cookies = []
    try:
        items = cookie_string.split(';')
        for item in items:
            if '=' in item:
                name, value = item.strip().split('=', 1)
                cookies.append({'name': name, 'value': value, 'domain': '.facebook.com'})
        return cookies
    except Exception:
        return []

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    
    # Path Detection
    chromium_path = shutil.which("chromium")
    chromedriver_path = shutil.which("chromedriver")
    
    # Fallback paths common in Streamlit Cloud / Linux
    if not chromium_path or not chromedriver_path:
        if os.path.exists("/usr/bin/chromium"): chromium_path = "/usr/bin/chromium"
        if os.path.exists("/usr/bin/chromedriver"): chromedriver_path = "/usr/bin/chromedriver"

    if chromium_path and chromedriver_path:
        chrome_options.binary_location = chromium_path
        service = Service(chromedriver_path)
        try:
            return webdriver.Chrome(service=service, options=chrome_options)
        except Exception as e:
            st.error(f"Driver Error: {e}")
            return None
    else:
        st.error("❌ Driver not found. Please ensure Chromium and Chromedriver are installed in packages.txt")
        return None

# --- HUNTER LOGIC (Popups Remover) ---
def hunt_down_buttons(driver):
    log("Hunter Mode Activated: Scanning for blocks...", "warn")
    
    for attempt in range(1, 6):
        try:
            # 1. Continue/Restore Buttons
            xpaths = [
                "//div[@role='button']//span[contains(text(), 'Continue')]",
                "//*[contains(text(), 'restore messages')]",
                "//div[@aria-label='Continue']"
            ]
            for xpath in xpaths:
                btns = driver.find_elements(By.XPATH, xpath)
                for btn in btns:
                    if btn.is_displayed():
                        driver.execute_script("arguments[0].click();", btn)
                        log(f"Hunter: Clicked Button ({attempt})", "success")
                        time.sleep(2)
            
            # 2. Close 'X' Button
            close_btns = driver.find_elements(By.CSS_SELECTOR, 'div[aria-label="Close"]')
            for btn in close_btns:
                driver.execute_script("arguments[0].click();", btn)
                log("Hunter: Closed Popup X", "info")
                
        except Exception:
            pass
        
        # Check if message box visible
        try:
            if driver.find_elements(By.CSS_SELECTOR, 'div[aria-label="Message"]'):
                log("Target Destroyed. Path Clear! ✅", "success")
                return True
        except:
            pass
        time.sleep(1)

# --- 🔥 SAFE SEND LOGIC (The Fix) 🔥 ---
def send_message_safely(driver, text):
    """
    Bypasses Interception Error:
    1. Finds Element.
    2. Sets Focus via Javascript (No click).
    3. Types via ActionChains (Ignores overlays).
    """
    selectors = [
        'div[aria-label="Message"]', 
        'div[contenteditable="true"]', 
        'div[role="textbox"]'
    ]
    
    msg_box = None
    for selector in selectors:
        try:
            msg_box = driver.find_element(By.CSS_SELECTOR, selector)
            if msg_box: break
        except:
            continue
            
    if msg_box:
        try:
            # STEP 1: Scroll to element
            driver.execute_script("arguments[0].scrollIntoView(true);", msg_box)
            time.sleep(0.5)

            # STEP 2: Javascript Force Focus (Click Fix)
            driver.execute_script("arguments[0].focus();", msg_box)
            # Optional: safe click via JS
            driver.execute_script("arguments[0].click();", msg_box) 
            time.sleep(0.5)
            
            # STEP 3: ActionChains Typing
            actions = ActionChains(driver)
            actions.send_keys(text)
            actions.send_keys(Keys.RETURN)
            actions.perform()
            
            return True
        except Exception as e:
            log(f"Send Error (Retrying): {e}", "error")
            return False
    else:
        log("Message Box Not Found for Sending", "error")
        return False

# --- MAIN EXECUTION ---
if st.button("Start Messaging"):
    driver = get_driver()
    
    if driver:
        try:
            log("Opening Facebook...", "info")
            driver.get("https://www.facebook.com/")
            
            log("Injecting Cookies...", "info")
            cookies_list = parse_cookies(cookie_input)
            for cookie in cookies_list:
                try:
                    driver.add_cookie(cookie)
                except:
                    pass
            
            log(f"Navigating to Chat...", "info")
            driver.get(target_url)
            time.sleep(8) 

            # --- RUN HUNTER ---
            hunt_down_buttons(driver)
            
            # --- START SENDING LOOP ---
            count = 0
            keep_running = True
            
            # Progress bar for visual
            st.divider()
            latest_status = st.empty()
            
            while keep_running:
                success = send_message_safely(driver, message_text)
                
                if success:
                    count += 1
                    latest_status.success(f"Messages Sent: {count} ✅")
                    
                    if not enable_infinite:
                        keep_running = False 
                    else:
                        time.sleep(delay_time)
                else:
                    log("Failed to send. Retrying...", "warn")
                    # Screenshot for debugging
                    try:
                        driver.save_screenshot("debug_send_fail.png")
                        st.image("debug_send_fail.png", caption="Error View")
                    except:
                        pass
                    time.sleep(5)
                    # Retry Hunter if popup came back
                    hunt_down_buttons(driver)

            st.balloons()
            log("Task Completed Successfully.", "success")

        except Exception as e:
            st.error(f"Critical System Error: {e}")
        finally:
            # Only quit driver if we aren't looping forever or if an error occurred
            if not enable_infinite:
                driver.quit()
    
