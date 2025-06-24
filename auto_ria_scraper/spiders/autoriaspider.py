import scrapy


class AutoRiaSpider(scrapy.Spider):
    name = "autoriaspider"
    allowed_domains = ["auto.ria.com"]
    start_urls = ["https://auto.ria.com/uk/car/used/"]

    def parse(self, response):
        cars = response.css(
            "div.content-bar")

        for car in cars:
            title = car.css("a.address::attr(title)").get()
            url = car.css("a.address::attr(href)").get()

            yield {
                "title": title.strip() if title else None,
                "url": response.urljoin(url) if url else None,
            }

        next_page = response.css("a.page-link.next::attr(href)").get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)
