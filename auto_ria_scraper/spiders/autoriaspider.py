from datetime import datetime

import scrapy


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
        item = {}

        item["url"] = response.url
        item["datetime_found"] = response.headers.get("Date", "").decode() or datetime.utcnow().isoformat()

        item["title"] = response.css("h1.head::text").get()

        yield item
