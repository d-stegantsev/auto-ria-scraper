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

# Suppress webdriver-manager logs to avoid cluttering output
os.environ["WDM_LOG"] = "0"

# Configure logging to display messages with timestamp
logging.basicConfig(
    format="%(asctime)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO
)

# Read database configuration from environment variables or set defaults
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "autodb"),
    "user": os.getenv("DB_USER", "autoria"),
    "password": os.getenv("DB_PASS", "autoria"),
    "host": os.getenv("DB_HOST", "postgres"),
    "port": os.getenv("DB_PORT", "5432"),
}

# Download and set up ChromeDriver for all workers (to avoid race conditions)
DRIVER_PATH = ChromeDriverManager().install()

# Set multiprocessing to 'fork' to allow driver sharing between processes (Linux/Unix)
multiprocessing.set_start_method('fork', force=True)

def get_db_connection():
    """
    Establish and return a connection to the PostgreSQL database.
    """
    return psycopg2.connect(**DB_CONFIG)

def format_phone_number(phone):
    """
    Normalize and format a phone number.
    - If phone is None or empty, returns None.
    - Strips non-digit characters.
    - Adds '38' country code for Ukrainian numbers starting with '0' and 10 digits.
    """
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("0") and len(digits) == 10:
        return "38" + digits
    return digits

def update_phone_number(conn, car_id, phone, status):
    """
    Update the phone number and phone status for a specific car in the database.
    """
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE cars SET phone_number=%s, phone_status=%s WHERE id=%s",
            (phone, status, car_id),
        )
    conn.commit()

def create_driver():
    """
    Create and configure a headless Chrome WebDriver instance.
    """
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    service = Service(DRIVER_PATH)
    return webdriver.Chrome(service=service, options=options)

def get_phone_number(driver, url):
    """
    Fetch and return the phone number from a car listing page using Selenium.
    - Waits for the phone span element.
    - Tries to click the 'show phone' link if present.
    - Waits until a valid phone number is loaded (not masked).
    """
    driver.get(url)
    # Wait for the phone number element to appear
    span = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "span.phone.bold"))
    )
    try:
        # Try to click the link that reveals the phone number
        link = span.find_element(By.CSS_SELECTOR, "a.phone_show_link")
        driver.execute_script("arguments[0].click();", link)
    except Exception:
        # It's okay if the link is not present (number may already be shown)
        pass
    # Wait until the phone number is available and not masked
    WebDriverWait(driver, 10).until(
        lambda d: span.get_attribute("data-phone-number") and "xxx" not in span.get_attribute("data-phone-number")
    )
    return span.get_attribute("data-phone-number")

def worker():
    """
    Worker process that:
    - Fetches pending/error car records from DB
    - Updates status to 'in_progress'
    - Extracts phone number from the page via Selenium
    - Updates the DB with the fetched number and status
    - Runs in a loop until no jobs left (then sleeps)
    """
    name = multiprocessing.current_process().name
    logging.info(f"Worker {name} started, polling for jobs")
    driver = create_driver()
    conn = get_db_connection()
    try:
        while True:
            # Fetch next car with pending/error phone status (locked for this transaction)
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
                # No jobs left, sleep before next poll
                time.sleep(5)
                continue
            car_id, url = row
            # Mark the record as 'in_progress'
            with conn:
                cur2 = conn.cursor()
                cur2.execute(
                    "UPDATE cars SET phone_status='in_progress' WHERE id=%s",
                    (car_id,),
                )
            try:
                # Try to extract phone number using Selenium
                phone = get_phone_number(driver, url)
                phone = format_phone_number(phone)
                status = "success"
            except Exception as e:
                # Log any errors and mark status as 'error'
                logging.error(f"Worker {name}: error fetching phone for car {car_id}: {e}")
                phone = None
                status = "error"
            # Update DB with result (phone number and new status)
            update_phone_number(conn, car_id, phone, status)
    finally:
        # Cleanup: close browser and DB connection
        driver.quit()
        conn.close()
        logging.info(f"Worker {name} shutdown")

def main():
    """
    Main process that spawns multiple worker processes and keeps the script alive.
    Handles graceful shutdown on keyboard interrupt.
    """
    start_time = datetime.datetime.now()
    logging.info("Spawning workers")
    num_workers = int(os.getenv("NUM_WORKERS", "4"))
    processes = []
    for i in range(num_workers):
        p = multiprocessing.Process(target=worker, name=f"worker-{i+1}")
        p.daemon = True
        p.start()
        processes.append(p)
    # Main loop keeps script alive while workers do their job
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        # Graceful shutdown on Ctrl+C
        logging.info("Shutdown signal received, terminating workers")
        for p in processes:
            p.terminate()
        elapsed = (datetime.datetime.now() - start_time).total_seconds()
        logging.info(f"Total runtime: {elapsed:.2f} seconds")

if __name__ == "__main__":
    main()
