import scrapy

class AutoRiaItem(scrapy.Item):
    url = scrapy.Field()
    title = scrapy.Field()
    price_usd = scrapy.Field()
    odometer = scrapy.Field()
    username = scrapy.Field()
    phone_number = scrapy.Field()
    image_url = scrapy.Field()
    images_count = scrapy.Field()
    car_number = scrapy.Field()
    car_vin = scrapy.Field()
    datetime_found = scrapy.Field()
