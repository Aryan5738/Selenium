import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.service import Service
import chromedriver_autoinstaller
import time
import os


# ==========================
# FACEBOOK COOKIES
# ==========================
cookies = [
    {"name": "sb", "value": "x-4VZxbqkmCAawFwsNZch1cr"},
    {"name": "m_pixel_ratio", "value": "2"},
    {"name": "ps_l", "value": "1"},
    {"name": "ps_n", "value": "1"},
    {"name": "usida", "value": "eyJ2ZXIiOjEsImlkIjoiQXNwa3poZzFqMWYwbmsiLCJ0aW1lIjoxNzM2MDIyNjM2fQ=="},
    {"name": "oo", "value": "v1"},
    {"name": "vpd", "value": "v1;634x360x2"},
    {"name": "x-referer", "value": "eyJyIjoiL2NoZWNrcG9pbnQvMTUwMTA5MjgyMzUyNTI4Mi9sb2dvdXQvP25leHQ9aHR0cHMlM0ElMkYlMkZtLmZhY2Vib29rLmNvbSUyRiIsImgiOiIvY2hlY2twb2ludC8xNTAxMDkyODIzNTI1MjgyL2xvZ291dC8/bmV4dD1odHRwcyUzQSUyRiUyRm0uZmFjZWJvb2suY29tJTJGIiwicyI6Im0ifQ=="},
    {"name": "pas", "value": "100018459948597:yY8iKAz4qS,61576915895165:h3M07gRmIr,100051495735634:aWZGIhmpcN,100079959253161:ERjtJDwIKY,100085135237853:SJzxBm80J0,100039111611241:YdPtkzDOqQ,61551133266466:w3egO2jjPR,61580506865263:gBocX6ACyH,61580725287646:z32vfC8XFx,61580627947722:NGvvqUwSjM,61580696818474:OANvC0tEZ7"},
    {"name": "locale", "value": "en_GB"},
    {"name": "c_user", "value": "61580506865263"},
    {"name": "datr", "value": "g8olaZiZYQMO7uPOZr9LIPht"},
    {"name": "xs", "value": "13:QoLIRrRzRReDAA:2:1764084356:-1:-1"},
    {"name": "wl_cbv", "value": "v2;client_version:2985;timestamp:1764084357"},
    {"name": "fbl_st", "value": "100727294;T:29401406"},
    {"name": "fr", "value": "1DU5Jl03wP4b7GP8t.AWefU_KjBG8Z5AZgumwZsBRycYqwUkK410GOJ9ACH6HquX9_4fk.BoxuDH..AAA.0.0.BpJcqK.AWdFN0M6cD-SLsdpO8kcmDP_8_s"},
    {"name": "presence", "value": "C{\"lm3\":\"sc.800019873203125\",\"t3\":[{\"o\":0,\"i\":\"g.1160300088952219\"}],\"utc3\":1764084412300,\"v\":1}"},
    {"name": "wd", "value": "1280x2254"}
]

THREAD_ID = "800019873203125"



# ==========================
# Selenium Driver Setup (AUTO INSTALL)
# ==========================
def get_driver():
    # Auto install correct chrome driver
    chromedriver_autoinstaller.install()

    # Check system chrome driver path
    chrome_path = "/usr/bin/chromedriver"

    if not os.path.exists(chrome_path):
        chrome_path = os.path.join(os.getcwd(), "chromedriver")  # auto-installed

    chrome_options = Options()
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_argument("--headless=new")

    service = Service(chrome_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver



# ==========================
# LOGIN WITH COOKIES
# ==========================
def login_with_cookies(driver):
    driver.get("https://www.facebook.com/")
    time.sleep(3)

    for c in cookies:
        try:
            driver.add_cookie(c)
        except:
            pass

    driver.refresh()
    time.sleep(4)



# ==========================
# SEND MESSAGE
# ==========================
def send_msg(driver, msg, delay):
    url = f"https://www.facebook.com/messages/e2ee/t/{THREAD_ID}"
    driver.get(url)
    time.sleep(5)

    try:
        box = driver.find_element(By.CSS_SELECTOR, "div[aria-label='Message']")
        ActionChains(driver).move_to_element(box).click().perform()
        box.send_keys(msg)

        time.sleep(1)

        send_btn = driver.find_element(By.CSS_SELECTOR, "div[aria-label='Press Enter to send']")
        send_btn.click()

        time.sleep(delay)
        return True

    except Exception as e:
        return str(e)



# ==========================
# STREAMLIT UI
# ==========================
st.title("🚀 Facebook Auto Message Sender (Selenium + Cookies + Streamlit)")

message = st.text_area("✉ Message", height=100)
delay = st.number_input("⏱ Delay (seconds)", min_value=1, max_value=60, value=3)
start = st.button("🔥 Send Message")

if start:
    if message.strip() == "":
        st.error("⚠ Message khaali hai veer!")
    else:
        st.info("🔄 Chrome start ho reha...")
        driver = get_driver()

        st.info("🔑 Cookie Login...")
        login_with_cookies(driver)

        st.info("📨 Message bhej reha...")
        status = send_msg(driver, message, delay)

        if status is True:
            st.success("✅ Successfully Sent!")
        else:
            st.error(f"❌ Error: {status}")

        driver.quit()
