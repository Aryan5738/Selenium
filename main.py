import streamlit as st
import os
import time
import shutil
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

st.set_page_config(page_title="FB Auto Sender", layout="centered")
st.title("FB Sender (The Hunter 🎯)")

# --- USER INPUTS ---
st.subheader("1. Login Details")
DEFAULT_COOKIE = "Sb=x-4VZxbqkmCAawFwsNZch1cr; m_pixel_ratio=2; ps_l=1; ps_n=1; usida=eyJ2ZXIiOjEsImlkIjoiQXNwa3poZzFqMWYwbmsiLCJ0aW1lIjoxNzM2MDIyNjM2fQ%3D%3D; oo=v1; vpd=v1%3B634x360x2; x-referer=eyJyIjoiL2NoZWNrcG9pbnQvMTUwMTA5MjgyMzUyNTI4Mi9sb2dvdXQvP25leHQ9aHR0cHMlM0ElMkYlMkZtLmZhY2Vib29rLmNvbSUyRiIsImgiOiIvY2hlY2twb2ludC8xNTAxMDkyODIzNTI1MjgyL2xvZ291dC8%2FbmV4dD1odHRwcyUzQSUyRiUyRm0uZmFjZWJvb2suY29tJTJGIiwicyI6Im0ifQ%3D%3D; pas=100018459948597%3AyY8iKAz4qS%2C61576915895165%3Ah3M07gRmIr%2C100051495735634%3AaWZGIhmpcN%2C100079959253161%3AERjtJDwIKY%2C100085135237853%3ASJzxBm80J0%2C100039111611241%3AYdPtkzDOqQ%2C61551133266466%3Aw3egO2jjPR%2C61580506865263%3AgBocX6ACyH%2C61580725287646%3Az32vfC8XFx%2C61580627947722%3NGvvqUwSjM%2C61580696818474%3AOANvC0tEZ7; locale=en_GB; c_user=61580506865263; datr=g8olaZiZYQMO7uPOZr9LIPht; xs=13%3AQoLIRrRzRReDAA%3A2%3A1764084356%3A-1%3A-1; wl_cbv=v2%3Bclient_version%3A2985%3Btimestamp%3A1764084357; fbl_st=100727294%3BT%3A29401406; fr=1DU5Jl03wP4b7GP8t.AWefU_KjBG8Z5AZgumwZsBRycYqwUkK410GOJ9ACH6HquX9_4fk.BoxuDH..AAA.0.0.BpJcqK.AWdFN0M6cD-SLsdpO8kcmDP_8_s; presence=C%7B%22lm3%22%3A%22sc.800019873203125%22%2C%22t3%22%3A%5B%7B%22o%22%3A0%2C%22i%22%3A%22g.1160300088952219%22%7D%5D%2C%22utc3%22%3A1764084412300%2C%22v%22%3A1%7D; wd=1280x2254; dpr=2"

cookie_input = st.text_area("Cookie String", value=DEFAULT_COOKIE, height=100)
user_pin = st.text_input("Enter 6-Digit PIN (Optional)", max_chars=6, type="password")

st.subheader("2. Message Details")
target_url = st.text_input("Chat URL", value="https://www.facebook.com/messages/e2ee/t/800019873203125")
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
    
    chromium_path = shutil.which("chromium")
    chromedriver_path = shutil.which("chromedriver")
    
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
        st.error("❌ Driver not found. Please REBOOT App.")
        return None

# --- 🔥 ADVANCED HUNTER LOGIC 🔥 ---
def hunt_down_buttons(driver):
    """
    यह फंक्शन एक 'शिकारी' की तरह है। यह Continue, Restore और Close बटन को ढूंढेगा
    और तब तक क्लिक करेगा जब तक Message Box नहीं मिल जाता।
    """
    st.info("⚔️ Hunter Mode Activated: Smashing Buttons...")

    # हम 7 बार कोशिश करेंगे (Trying... Trying...)
    for attempt in range(1, 8):
        status_text = st.empty()
        status_text.text(f"Attempt {attempt}/7: Scanning for blocks...")
        
        button_clicked = False
        
        # --- TARGET 1: CONTINUE BUTTON (Blue one from screenshot) ---
        try:
            # Strategies to find 'Continue'
            xpaths = [
                "//div[@role='button']//span[contains(text(), 'Continue')]", # Best match
                "//*[text()='Continue']",
                "//div[@aria-label='Continue']"
            ]
            
            for xpath in xpaths:
                btns = driver.find_elements(By.XPATH, xpath)
                for btn in btns:
                    if btn.is_displayed():
                        driver.execute_script("arguments[0].click();", btn)
                        st.toast("Boom! Clicked 'Continue' 🔵")
                        button_clicked = True
                        time.sleep(2)
        except:
            pass

        # --- TARGET 2: DON'T RESTORE BUTTON ---
        try:
            btns = driver.find_elements(By.XPATH, "//*[contains(text(), 'restore messages')]")
            for btn in btns:
                 driver.execute_script("arguments[0].click();", btn)
                 st.toast("Boom! Clicked 'Don't Restore' 🛑")
                 button_clicked = True
                 time.sleep(2)
        except:
            pass

        # --- TARGET 3: CLOSE (X) BUTTON ---
        try:
            close_btns = driver.find_elements(By.CSS_SELECTOR, 'div[aria-label="Close"]')
            for btn in close_btns:
                driver.execute_script("arguments[0].click();", btn)
                st.toast("Closed Popup ❎")
                button_clicked = True
        except:
            pass

        # --- CHECK SUCCESS ---
        # अगर बटन दबाया है, तो चेक करो कि क्या मैसेज बॉक्स खुला?
        try:
            msg_box = driver.find_element(By.CSS_SELECTOR, 'div[aria-label="Message"]')
            if msg_box:
                status_text.success("Target Destroyed. Message Box Found! ✅")
                return True
        except:
            pass
        
        time.sleep(2) # अगली कोशिश से पहले सांस लो

    return False

# --- MAIN EXECUTION ---

if st.button("Start Messaging"):
    status_box = st.empty()
    log_box = st.empty()
    
    driver = get_driver()
    
    if driver:
        try:
            status_box.text("Opening Facebook...")
            driver.get("https://www.facebook.com/")
            
            status_box.text("Adding Cookies...")
            cookies_list = parse_cookies(cookie_input)
            for cookie in cookies_list:
                try:
                    driver.add_cookie(cookie)
                except:
                    pass
            
            status_box.text("Opening Chat...")
            driver.get(target_url)
            time.sleep(8) 

            # --- 🔥 RUN THE HUNTER 🔥 ---
            hunt_down_buttons(driver)
            # --------------------------

            msg_box = None
            selectors = [
                'div[aria-label="Message"]', 
                'div[contenteditable="true"]', 
                'div[role="textbox"]'
            ]

            # Try to find message box
            for selector in selectors:
                try:
                    msg_box = driver.find_element(By.CSS_SELECTOR, selector)
                    if msg_box: break
                except:
                    continue
            
            if msg_box:
                count = 0
                keep_running = True
                while keep_running:
                    try:
                        # Re-find logic
                        for selector in selectors:
                            try:
                                msg_box = driver.find_element(By.CSS_SELECTOR, selector)
                                break
                            except:
                                continue

                        msg_box.click()
                        msg_box.send_keys(message_text)
                        msg_box.send_keys(Keys.RETURN)
                        
                        count += 1
                        log_box.write(f"Messages Sent: {count} ✅")
                        
                        if not enable_infinite:
                            keep_running = False 
                        else:
                            time.sleep(delay_time)
                    except Exception as e:
                        st.error(f"Sending Error: {e}")
                        break
                st.success("Done.")
            else:
                st.error("Message Box Not Found.")
                st.caption("Last Screen State:")
                driver.save_screenshot("final_check.png")
                st.image("final_check.png")

        except Exception as e:
            st.error(f"Critical Error: {e}")
        finally:
            if not enable_infinite:
                driver.quit()
