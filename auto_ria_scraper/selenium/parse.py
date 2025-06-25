import time
import tempfile
import psycopg2
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

os.environ["WDM_LOG"] = "0"

DB_CONFIG = dict(
    dbname=os.getenv("DB_NAME", "autodb"),
    user=os.getenv("DB_USER", "autoria"),
    password=os.getenv("DB_PASS", "autoria"),
    host=os.getenv("DB_HOST", "postgres"),
    port=os.getenv("DB_PORT", 5432),
)

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def has_pending_records(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT EXISTS (SELECT 1 FROM cars WHERE phone_status = 'pending')")
        exists, = cur.fetchone()
        return exists

def get_pending_urls(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT id, url FROM cars WHERE phone_status = 'pending'")
        rows = cur.fetchall()
        return rows

def get_phone_number(url):
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    with tempfile.TemporaryDirectory() as user_data_dir:
        options.add_argument(f"--user-data-dir={user_data_dir}")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        try:
            driver.get(url)
            try:
                btn = driver.find_element(By.CSS_SELECTOR, "a.phone_show_link")
                btn.click()
            except Exception:
                pass
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            phone_span = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "span[data-phone-number]"))
            )
            phone = phone_span.get_attribute("data-phone-number")
            if not phone:
                phone = phone_span.text.strip()
            return phone
        except Exception as ex:
            print(f"Error for {url}: {ex}")
            return None
        finally:
            driver.quit()


def update_phone_number(conn, car_id, phone, status):
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE cars SET phone_number=%s, phone_status=%s WHERE id=%s",
            (phone, status, car_id)
        )
        conn.commit()

def main():
    print("Starting Selenium phone parser polling...")
    while True:
        try:
            with get_db_connection() as conn:
                rows = get_pending_urls(conn)
                if not rows:
                    print("No pending records. Sleeping 15s…")
                    time.sleep(15)
                    continue

                print("DB_CONFIG:", DB_CONFIG)
                print("has pending? →", bool(get_pending_urls(conn)))

                rows = get_pending_urls(conn)
                for car_id, url in rows:
                    print(f"Processing car id={car_id} url={url}")
                    phone = get_phone_number(url)
                    status = "success" if phone else "error"
                    update_phone_number(conn, car_id, phone, status)
        except Exception as ex:
            print(f"Main loop exception: {ex}")
            time.sleep(10)

if __name__ == "__main__":
    main()
