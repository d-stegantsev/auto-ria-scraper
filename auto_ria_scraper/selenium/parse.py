import re
import time
import psycopg2
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

os.environ["WDM_LOG"] = "0"

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "autodb"),
    "user": os.getenv("DB_USER", "autoria"),
    "password": os.getenv("DB_PASS", "autoria"),
    "host": os.getenv("DB_HOST", "postgres"),
    "port": os.getenv("DB_PORT", "5432"),
}

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def get_pending_urls(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT id, url FROM cars WHERE phone_status = 'pending'")
        return cur.fetchall()

def format_phone_number(phone):
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("0") and len(digits) == 10:
        return "38" + digits
    return digits

def update_phone_number(conn, car_id, phone, status):
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE cars SET phone_number=%s, phone_status=%s WHERE id=%s",
            (phone, status, car_id),
        )
    conn.commit()

def create_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def get_phone_number(driver, url):
    driver.get(url)
    span = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "span.phone.bold"))
    )
    initial = span.get_attribute("data-phone-number")
    try:
        link = span.find_element(By.CSS_SELECTOR, "a.phone_show_link")
        driver.execute_script("arguments[0].click();", link)
    except Exception as e:
        print(f"Click error for {url}: {e}")
    WebDriverWait(driver, 10).until(
        lambda d: span.get_attribute("data-phone-number") and "xxx" not in span.get_attribute("data-phone-number")
    )
    return span.get_attribute("data-phone-number")

def main():
    print("▶ Starting Selenium phone parser polling…")
    driver = create_driver()
    try:
        while True:
            with get_db_connection() as conn:
                rows = get_pending_urls(conn)
                if not rows:
                    print("No pending records. Sleeping 5s…")
                    time.sleep(5)
                    continue

                for car_id, url in rows:
                    try:
                        phone = get_phone_number(driver, url)
                        phone = format_phone_number(phone)
                        status = "success"
                    except Exception as ex:
                        print(f"Error parsing {url}: {ex}")
                        phone = None
                        status = "error"
                    update_phone_number(conn, car_id, phone, status)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
