import re
import time
import psycopg2
import os
import multiprocessing
import datetime
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Suppress webdriver-manager logs
os.environ["WDM_LOG"] = "0"

# Logging configuration
logging.basicConfig(
    format="%(asctime)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO
)

# Database configuration
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "autodb"),
    "user": os.getenv("DB_USER", "autoria"),
    "password": os.getenv("DB_PASS", "autoria"),
    "host": os.getenv("DB_HOST", "postgres"),
    "port": os.getenv("DB_PORT", "5432"),
}

# Pre-install ChromeDriver once to avoid concurrent writes from multiple processes
DRIVER_PATH = ChromeDriverManager().install()

# Ensure fork start method to share DRIVER_PATH
multiprocessing.set_start_method('fork', force=True)

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

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
    service = Service(DRIVER_PATH)
    return webdriver.Chrome(service=service, options=options)

def get_phone_number(driver, url):
    driver.get(url)
    span = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "span.phone.bold"))
    )
    try:
        link = span.find_element(By.CSS_SELECTOR, "a.phone_show_link")
        driver.execute_script("arguments[0].click();", link)
    except Exception:
        pass
    WebDriverWait(driver, 10).until(
        lambda d: span.get_attribute("data-phone-number") and "xxx" not in span.get_attribute("data-phone-number")
    )
    return span.get_attribute("data-phone-number")

def worker():
    name = multiprocessing.current_process().name
    logging.info(f"Worker {name} started, polling for jobs")
    driver = create_driver()
    conn = get_db_connection()
    try:
        while True:
            # Fetch pending first, then retry any error statuses
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, url FROM cars "
                    "WHERE phone_status IN ('pending','error') "
                    "ORDER BY CASE WHEN phone_status='pending' THEN 0 ELSE 1 END "
                    "LIMIT 1 "
                    "FOR UPDATE SKIP LOCKED"
                )
                row = cur.fetchone()
            if not row:
                time.sleep(5)
                continue
            car_id, url = row
            # Mark as in progress
            with conn:
                cur2 = conn.cursor()
                cur2.execute(
                    "UPDATE cars SET phone_status='in_progress' WHERE id=%s",
                    (car_id,),
                )
            try:
                phone = get_phone_number(driver, url)
                phone = format_phone_number(phone)
                status = "success"
            except Exception as e:
                logging.error(f"Worker {name}: error fetching phone for car {car_id}: {e}")
                phone = None
                status = "error"
            update_phone_number(conn, car_id, phone, status)
            logging.info(f"Worker {name}: Car {car_id} -> status={status}, phone={phone}")
    finally:
        driver.quit()
        conn.close()
        logging.info(f"Worker {name} shutdown")

def main():
    start_time = datetime.datetime.now()
    logging.info("Spawning workers")
    num_workers = int(os.getenv("NUM_WORKERS", "4"))
    processes = []
    for i in range(num_workers):
        p = multiprocessing.Process(target=worker, name=f"worker-{i+1}")
        p.daemon = True
        p.start()
        processes.append(p)
    # Keep main alive to allow workers to run
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logging.info("Shutdown signal received, terminating workers")
        for p in processes:
            p.terminate()
        elapsed = (datetime.datetime.now() - start_time).total_seconds()
        logging.info(f"Total runtime: {elapsed:.2f} seconds")

if __name__ == "__main__":
    main()
