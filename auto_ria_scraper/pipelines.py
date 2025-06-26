import os
from psycopg2.extras import execute_values
from datetime import datetime
import psycopg2

# Read database configuration from environment variables (or set defaults)
db_name = os.getenv("DB_NAME", "autodb")
db_user = os.getenv("DB_USER", "autoria")
db_pass = os.getenv("DB_PASS", "autoria")
db_host = os.getenv("DB_HOST", "postgres")
db_port = int(os.getenv("DB_PORT", 5432))

class PostgresPipeline:
    """
    Pipeline to save scraped items to PostgreSQL in batches.
    """

    def open_spider(self, spider):
        """
        Called when the spider is opened.
        - Opens a database connection.
        - Prepares a cursor and initializes the items buffer.
        """
        self.conn = psycopg2.connect(
            dbname=db_name,
            user=db_user,
            password=db_pass,
            host=db_host,
            port=db_port,
        )
        self.cur = self.conn.cursor()
        self.items = []

    def close_spider(self, spider):
        """
        Called when the spider is closed.
        - Saves any remaining items that have not yet been inserted.
        - Closes the cursor and the connection.
        """
        if self.items:
            self.save_items()
        self.cur.close()
        self.conn.close()

    def process_item(self, item, spider):
        """
        Called for every item pipeline component.
        - Adds the item to a buffer.
        - Once the buffer reaches 100 items, saves all at once to the database.
        """
        self.items.append(item)
        if len(self.items) >= 100:
            self.save_items()
            self.items = []
        return item

    def save_items(self):
        """
        Bulk-inserts all buffered items into the 'cars' table.
        - Uses ON CONFLICT DO NOTHING to avoid inserting duplicate URLs.
        - Inserts all columns scraped by the spider (except phone_number, which is set to None here and updated later).
        """
        sql = """
        INSERT INTO cars
        (url, title, price_usd, odometer, username, phone_number, image_url, images_count, car_number, car_vin, datetime_found)
        VALUES %s
        ON CONFLICT (url) DO NOTHING
        """
        values = [
            (
                i.get("url"),
                i.get("title"),
                i.get("price_usd"),
                i.get("odometer"),
                i.get("username"),
                None,  # phone_number is set by Selenium parser later
                i.get("image_url"),
                i.get("images_count"),
                i.get("car_number"),
                i.get("car_vin"),
                i.get("datetime_found") or datetime.now()
            )
            for i in self.items
        ]
        execute_values(self.cur, sql, values)
        self.conn.commit()
