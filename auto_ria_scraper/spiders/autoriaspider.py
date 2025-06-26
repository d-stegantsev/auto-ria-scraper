import scrapy
from datetime import datetime, timezone, timedelta
import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from auto_ria_scraper.items import AutoRiaItem


class AutoRiaSpider(scrapy.Spider):
    # Name of the spider; used to run it with 'scrapy crawl autoriaspider'
    name = "autoriaspider"
    # Allowed domains for scraping (prevents the spider from crawling external links)
    allowed_domains = ["auto.ria.com"]
    # Starting URL (first page of the car listings)
    start_urls = ["https://auto.ria.com/uk/search/?lang_id=4&page=0&countpage=100&indexName=auto&custom=1&abroad=2"]
    # Limit for maximum pages to crawl (for efficiency/testing)
    max_pages = 30

    def parse(self, response):
        """
        Main parse method for listing pages.
        - Extracts individual car links from the search results and schedules parsing their details.
        - Handles pagination up to max_pages, constructing next page URLs dynamically.
        """
        cars = response.css("div.content-bar")
        if not cars:
            # If no car items found, stop parsing this page.
            return
        for car in cars:
            url = car.css("a.address::attr(href)").get()
            if url:
                # Schedule a request for the car detail page
                yield response.follow(url, callback=self.parse_car_detail)

        # Handle pagination: extract current page number, build next page URL
        parsed = urlparse(response.url)
        qs = parse_qs(parsed.query)
        current_page = int(qs.get("page", ["0"])[0])
        if current_page < self.max_pages:
            next_page = current_page + 1
            qs["page"] = [str(next_page)]
            new_query = urlencode(qs, doseq=True)
            next_url = urlunparse(parsed._replace(query=new_query))
            # Schedule the next page for parsing
            yield scrapy.Request(next_url, callback=self.parse)
        else:
            # Log a message if maximum page limit reached
            self.logger.info(f"Reached max page {self.max_pages}, stopping pagination")

    def parse_car_detail(self, response):
        """
        Parse the detail page for a single car.
        - Extracts car attributes (title, price, odometer, seller, images, VIN, etc.)
        - Returns an item with all scraped information.
        """
        item = AutoRiaItem()
        item["url"] = response.url

        # Extract car title (strip whitespace, handle missing case)
        item["title"] = response.css("h1.head::text").get().strip() if response.css("h1.head::text").get() else None

        # Extract USD price (clean formatting, fallback if not found)
        price_usd_text = response.css("div.price_value--additional span[data-currency='USD']::text").get()
        if price_usd_text:
            price_clean = re.sub(r"[^\d]", "", price_usd_text)
            item["price_usd"] = int(price_clean) if price_clean.isdigit() else None
        else:
            price_text = response.css("div.price_value strong::text").get()
            if price_text:
                price_clean = re.sub(r"[^\d]", "", price_text)
                item["price_usd"] = int(price_clean) if price_clean.isdigit() else None
            else:
                item["price_usd"] = None

        # Extract odometer value (in thousands, handle parsing errors)
        odometer_span = response.css("div.base-information.bold span.size18::text").get()
        if odometer_span:
            try:
                odometer_val = int(odometer_span.strip())
                odometer = odometer_val * 1000
            except ValueError:
                odometer = None
        else:
            odometer = None
        item["odometer"] = odometer

        # Extract seller username (prefer modern class, fallback to classic)
        seller_area = response.css("div.seller_info_area")
        name_node = seller_area.css(".seller_info_name")
        if name_node:
            username = name_node.xpath("normalize-space(string(.))").get()
        else:
            raw = seller_area.css("a.sellerPro::text").get()
            username = raw.strip() if raw else None
        item["username"] = username

        # Extract main image from the photo blocks (first found)
        photo_blocks = response.xpath("//div[@class='photo-620x465']")
        main_image = None
        for block in photo_blocks:
            img_url = block.xpath(".//img[@class='outline m-auto']/@src").get()
            if img_url:
                main_image = img_url
                break
        item["image_url"] = main_image

        # Extract the count of images (from text or fallback to number of blocks)
        photos_text = response.css("a.show-all.link-dotted::text").get()
        images_count = None
        if photos_text:
            match = re.search(r"(\d+)", photos_text)
            if match:
                images_count = int(match.group(1))
        if images_count is None:
            images_count = len(photo_blocks)
        item["images_count"] = images_count

        # Extract car plate number (if exists)
        car_number = response.css("span.state-num.ua::text").get()
        item["car_number"] = car_number.strip() if car_number else None

        # Extract VIN number (if exists)
        vin = response.css("span.label-vin::text").get()
        item["car_vin"] = vin.strip() if vin else None

        # Record datetime of when this car was scraped (ISO8601 with UTC+3 offset)
        item["datetime_found"] = datetime.now(timezone(timedelta(hours=3))).isoformat()

        # Return the filled item to the pipeline
        yield item
