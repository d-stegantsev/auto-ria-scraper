import scrapy
from datetime import datetime, timezone, timedelta
import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from auto_ria_scraper.items import AutoRiaItem


class AutoRiaSpider(scrapy.Spider):
    name = "autoriaspider"
    allowed_domains = ["auto.ria.com"]
    start_urls = ["https://auto.ria.com/uk/search/?lang_id=4&page=0&countpage=100&indexName=auto&custom=1&abroad=2"]

    def parse(self, response):
        # Select car listings on the page
        cars = response.css("div.content-bar")
        if not cars:
            return
        for car in cars:
            url = car.css("a.address::attr(href)").get()
            if url:
                yield response.follow(url, callback=self.parse_car_detail)

        # Pagination logic: increment the page parameter and request next page
        parsed = urlparse(response.url)
        qs = parse_qs(parsed.query)
        current_page = int(qs.get("page", ["0"])[0])
        next_page = current_page + 1
        qs["page"] = [str(next_page)]
        new_query = urlencode(qs, doseq=True)
        next_url = urlunparse(parsed._replace(query=new_query))
        yield scrapy.Request(next_url, callback=self.parse)

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

        # Username
        seller_area = response.css("div.seller_info_area")
        name_node = seller_area.css(".seller_info_name")
        if name_node:
            username = name_node.xpath("normalize-space(string(.))").get()
        else:
            raw = seller_area.css("a.sellerPro::text").get()
            username = raw.strip() if raw else None
        item["username"] = username

        # Image URL
        photo_blocks = response.xpath("//div[@class='photo-620x465']")
        main_image = None
        for block in photo_blocks:
            img_url = block.xpath(".//img[@class='outline m-auto']/@src").get()
            if img_url:
                main_image = img_url
                break
        item["image_url"] = main_image

        # Images count
        photos_text = response.css("a.show-all.link-dotted::text").get()
        images_count = None
        if photos_text:
            match = re.search(r"(\d+)", photos_text)
            if match:
                images_count = int(match.group(1))
        if images_count is None:
            photo_blocks = response.xpath("//div[contains(@class, 'photo-620x465')]")
            images_count = len(photo_blocks)
        item["images_count"] = images_count

        # Car number
        car_number = response.css("span.state-num.ua::text").get()
        if car_number:
            car_number = car_number.strip()
        item["car_number"] = car_number

        # VIN
        vin = response.css("span.label-vin::text").get()
        if vin:
            vin = vin.strip()
        item["car_vin"] = vin

        # Record the found datetime with local timezone
        item["datetime_found"] = datetime.now(timezone(timedelta(hours=3))).isoformat()

        yield item
