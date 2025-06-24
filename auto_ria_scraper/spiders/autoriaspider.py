import scrapy
from datetime import datetime, timezone, timedelta
import re

from auto_ria_scraper.items import AutoRiaItem


class AutoRiaSpider(scrapy.Spider):
    name = "autoriaspider"
    allowed_domains = ["auto.ria.com"]
    start_urls = ["https://auto.ria.com/uk/car/used/"]

    def parse(self, response):
        cars = response.css("div.content-bar")
        for car in cars:
            url = car.css("a.address::attr(href)").get()
            if url:
                yield response.follow(url, callback=self.parse_car_detail)

        next_page = response.css("a.page-link.next::attr(href)").get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)

    def parse_car_detail(self, response):
        item = AutoRiaItem()

        item["url"] = response.url

        # Title
        item["title"] = response.css("h1.head::text").get()

        # Price USD

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

        # Odometer
        odometer_text = response.css("div.data-block span.value::text").re_first(r"[\d\s]+")
        if odometer_text:
            odometer_clean = re.sub(r"[^\d]", "", odometer_text)
            item["odometer"] = int(odometer_clean) if odometer_clean.isdigit() else None
        else:
            item["odometer"] = None

        # Username
        item["username"] = response.css("div.seller-name a::text").get()

        # Phone number
        phone_raw = response.css("a.phone-button::attr(data-phone)").get()
        item["phone_number"] = phone_raw if phone_raw else None

        # Image URL
        item["image_url"] = response.css("div.gallery img::attr(src)").get()

        # Images count
        images = response.css("div.gallery img")
        item["images_count"] = len(images)

        # Car number
        car_number = response.css("div.car-number span.value::text").get()
        item["car_number"] = car_number.strip() if car_number else None

        # VIN
        vin = response.css("div.vin span.value::text").get()
        item["car_vin"] = vin.strip() if vin else None

        item["datetime_found"] = datetime.now(timezone(timedelta(hours=3))).isoformat()

        yield item
