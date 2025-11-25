from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

# -------------- CONFIG -----------------
COOKIE_STRING = """sb=x-4VZxbqkmCAawFwsNZch1cr; m_pixel_ratio=2; ps_l=1; ps_n=1; usida=eyJ2ZXIiOjEsImlkIjoiQXNwa3poZzFqMWYwbmsiLCJ0aW1lIjoxNzM2MDIyNjM2fQ%3D%3D; oo=v1; vpd=v1%3B634x360x2; x-referer=eyJyIjoiL2NoZWNrcG9pbnQvMTUwMTA5MjgyMzUyNTI4Mi9sb2dvdXQvP25leHQ9aHR0cHMlM0ElMkYlMkZtLmZhY2Vib29rLmNvbSUyRiIsImgiOiIvY2hlY2twb2ludC8xNTAxMDkyODIzNTI1MjgyL2xvZ291dC8%2FbmV4dD1odHRwcyUzQSUyRiUyRm0uZmFjZWJvb2suY29tJTJGIiwicyI6Im0ifQ%3D%3D; pas=100018459948597%3AyY8iKAz4qS%2C61576915895165%3Ah3M07gRmIr%2C100051495735634%3AaWZGIhmpcN%2C100079959253161%3AERjtJDwIKY%2C100085135237853%3ASJzxBm80J0%2C100039111611241%3AYdPtkzDOqQ%2C61551133266466%3Aw3egO2jjPR%2C61580506865263%3AgBocX6ACyH%2C61580725287646%3Az32vfC8XFx%2C61580627947722%3ANGvvqUwSjM%2C61580696818474%3AOANvC0tEZ7; locale=en_GB; c_user=61580506865263; datr=g8olaZiZYQMO7uPOZr9LIPht; xs=13%3AQoLIRrRzRReDAA%3A2%3A1764084356%3A-1%3A-1; wl_cbv=v2%3Bclient_version%3A2985%3Btimestamp%3A1764084357; fbl_st=100727294%3BT%3A29401406; fr=1DU5Jl03wP4b7GP8t.AWefU_KjBG8Z5AZgumwZsBRycYqwUkK410GOJ9ACH6HquX9_4fk.BoxuDH..AAA.0.0.BpJcqK.AWdFN0M6cD-SLsdpO8kcmDP_8_s; presence=C%7B%22lm3%22%3A%22sc.800019873203125%22%2C%22t3%22%3A%5B%7B%22o%22%3A0%2C%22i%22%3A%22g.1160300088952219%22%7D%5D%2C%22utc3%22%3A1764084412300%2C%22v%22%3A1%7D; wd=1280x2254"""

CHAT_URL = "https://www.facebook.com/messages/e2ee/t/800019873203125"
MESSAGE = "aryan don hware yeh"
DELAY = 30   # seconds
# ---------------------------------------


def parse_cookies(cookie_string):
    cookies = []
    for item in cookie_string.split(";"):
        if "=" in item:
            name, value = item.split("=", 1)
            cookies.append({"name": name.strip(), "value": value.strip(), "domain": ".facebook.com"})
    return cookies


def get_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def start_bot():
    driver = get_driver()

    print("[*] Opening Facebook...")
    driver.get("https://www.facebook.com/")
    time.sleep(3)

    print("[*] Adding Cookies...")
    for c in parse_cookies(COOKIE_STRING):
        try:
            driver.add_cookie(c)
        except:
            pass

    driver.refresh()
    time.sleep(4)

    print("[*] Opening Chat...")
    driver.get(CHAT_URL)
    time.sleep(6)

    print("[*] Starting infinite messaging loop...")

    count = 1
    while True:
        try:
            box = driver.find_element(By.XPATH, "//div[@role='textbox']")
            box.click()
            box.send_keys(MESSAGE)
            time.sleep(1)
            box.send_keys("\ue007")  # ENTER

            print(f"[{count}] Sent: {MESSAGE}")
            count += 1

        except Exception as e:
            print("Error:", e)

        time.sleep(DELAY)


if __name__ == "__main__":
    start_bot()
