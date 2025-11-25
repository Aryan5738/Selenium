import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time
import json
import os

st.set_page_config(page_title="Facebook Auto Sender", layout="wide")

# ===== Custom HTML UI =====
st.markdown("""
    <style>
        .title {
            font-size: 36px;
            font-weight: 700;
            color: #4CAF50;
            text-align: center;
            padding: 10px;
        }
        .box {
            background: #ffffff;
            padding: 18px;
            border-radius: 12px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
            margin-bottom: 16px;
        }
        .log-box {
            background: #000;
            color: #0f0;
            padding: 15px;
            border-radius: 10px;
            height: 250px;
            overflow-y: scroll;
            font-family: monospace;
            font-size: 14px;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("<div class='title'>📨 Facebook Auto Message Sender</div>", unsafe_allow_html=True)


# ===== CHROMEDRIVER PATH =====
CHROME_DRIVER_PATH = os.path.abspath("chromedriver")


def get_driver(log):
    log("🔄 Starting Chrome...")
    chrome_options = Options()
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--headless=new")

    service = Service(CHROME_DRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    log("✅ Chrome started!")
    return driver


# ===== Add Cookie =====
def add_cookie(driver, cookie_json, log):
    log("🔑 Loading Facebook...")
    cookies = json.loads(cookie_json)

    driver.get("https://facebook.com")
    time.sleep(3)

    log("🍪 Adding Cookies...")
    for ck in cookies:
        try:
            driver.add_cookie(ck)
        except:
            pass

    driver.refresh()
    time.sleep(3)
    log("✅ Login success (cookie login)")


# ===== Send Message =====
def send_msg(driver, thread_id, msg, log):
    chat_link = f"https://www.facebook.com/messages/t/{thread_id}"

    log(f"📬 Opening chat → {chat_link}")
    driver.get(chat_link)
    time.sleep(5)

    log("⌨ Typing message...")
    box = driver.find_element(By.CSS_SELECTOR, "div[aria-label='Message']")
    box.send_keys(msg)
    time.sleep(1)

    log("📨 Clicking Send...")
    send = driver.find_element(By.CSS_SELECTOR, "div[aria-label='Press Enter to send']")
    send.click()

    log("🎉 Message Sent!")


# ===== UI Input Boxes =====
st.markdown("<div class='box'>", unsafe_allow_html=True)
cookie_input = st.text_area("🍪 Paste Your Facebook Cookies (JSON)", height=150)
thread_id = st.text_input("🔗 Thread ID (Messenger ID)")
message = st.text_area("✉ Message", height=120)
delay = st.number_input("⏱ Delay (seconds)", 1, 60, 3)
start = st.button("🚀 START SENDING")
st.markdown("</div>", unsafe_allow_html=True)

# ===== LOG UI BOX =====
st.markdown("<h4>📡 Live Logs</h4>", unsafe_allow_html=True)
log_box = st.empty()


def log(text):
    old = log_box.text_area("Logs", value="", height=250)
    log_box.text_area("Logs", value=old + text + "\n", height=250)


# ===== RUNNING PROCESS =====
if start:
    try:
        log("▶ PROCESS STARTED")
        driver = get_driver(log)

        add_cookie(driver, cookie_input, log)

        send_msg(driver, thread_id, message, log)

        time.sleep(delay)
        log("✅ DONE")

        driver.quit()

    except Exception as e:
        log(f"❌ ERROR: {str(e)}")
