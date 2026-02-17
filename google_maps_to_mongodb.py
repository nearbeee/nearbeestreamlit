from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pymongo import MongoClient
import os
import time
import re
from datetime import datetime

from category_utils import normalize_category


# ─── LOAD .env MANUALLY (no python-dotenv needed) ─────────────────────────────
def load_env():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))

load_env()

MONGO_URL = os.getenv("MONGO_URL")


# MONGODB CONNECTION

client = MongoClient(MONGO_URL)
db = client["test"]
collection = db["shops"]


# CLEAN PHONE

def clean_phone(phone):
    if not phone:
        return ""
    phone = re.sub(r"\D", "", phone)
    return phone[-10:]


# SCRAPER FUNCTION

def scrape_and_store(search_query):

    url = f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}"

    # ── Streamlit Cloud-compatible Chrome options ──────────────────────────────
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    # Try system chromedriver first (Streamlit Cloud), fall back to local .exe
    try:
        driver = webdriver.Chrome(options=options)
    except Exception:
        service = Service("chromedriver.exe")
        driver = webdriver.Chrome(service=service, options=options)

    wait = WebDriverWait(driver, 20)

    driver.get(url)
    time.sleep(6)

    scroll_div = wait.until(
        EC.presence_of_element_located(
            (By.XPATH, "//div[contains(@aria-label,'Results')]")
        )
    )

    for _ in range(12):
        driver.execute_script(
            "arguments[0].scrollTop = arguments[0].scrollHeight",
            scroll_div
        )
        time.sleep(2)

    shops = driver.find_elements(By.CSS_SELECTOR, "div[role='article']")
    print(f" SCRAPING STARTED: {search_query}")

    for shop in shops:
        try:
            link = shop.find_element(By.CSS_SELECTOR, "a.hfpxzc")
            shop_name = link.get_attribute("aria-label")
            href = link.get_attribute("href")

            lat = re.search(r"!3d([-0-9.]+)", href)
            lng = re.search(r"!4d([-0-9.]+)", href)
            if not lat or not lng:
                continue

            #  DUPLICATE CHECK
            existing = collection.find_one({
                "shopName": shop_name,
                "latitude": float(lat.group(1)),
                "longitude": float(lng.group(1))
            })

            if existing:
                print(f"⏭️ DUPLICATE SKIPPED: {shop_name}")
                continue

            driver.execute_script("window.open(arguments[0]);", href)
            driver.switch_to.window(driver.window_handles[1])
            time.sleep(4)

            try:
                raw_category = driver.find_element(
                    By.XPATH, "//button[contains(@jsaction,'category')]"
                ).text.strip()
            except:
                raw_category = ""

            category = normalize_category(raw_category)

            try:
                raw_phone = driver.find_element(
                    By.XPATH, "//button[contains(@aria-label,'Phone')]"
                ).get_attribute("aria-label")
                contact = clean_phone(raw_phone)
            except:
                contact = ""

            try:
                address = driver.find_element(
                    By.XPATH, "//button[@data-item-id='address']"
                ).get_attribute("aria-label").replace("Address: ", "")
            except:
                address = ""

            try:
                image = driver.find_element(
                    By.XPATH, "//img[contains(@src,'googleusercontent.com')]"
                ).get_attribute("src")
            except:
                image = ""

            driver.close()
            driver.switch_to.window(driver.window_handles[0])

            now = datetime.utcnow().isoformat() + "Z"

            # FORMAT
            shop_data = {
                "ownerName": "NA",
                "shopName": shop_name,
                "contactNumber": contact,
                "email": "NA",
                "category": category,
                "address": address,
                "latitude": float(lat.group(1)),
                "longitude": float(lng.group(1)),
                "shopImage": image,
                "createdAt": now,
                "updatedAt": now,
            }

            collection.insert_one(shop_data)
            print(f"✅ INSERTED: {shop_name}")

        except Exception as e:
            print("❌ ERROR:", e)

    driver.quit()
    print("SCRAPING DONE")