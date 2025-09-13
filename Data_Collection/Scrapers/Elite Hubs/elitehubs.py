import requests
import json
import re
from fake_useragent import UserAgent
import time
import scrapy
from bs4 import BeautifulSoup


url = "https://www.elitehubs.com/collections/processors"
requests.session()
headers = {
    "User-Agent": UserAgent().random
}
page = 1

class EliteHubsSpider(scrapy.Spider):
    name = "elitehubs"
    allowed_domains = ["elitehubs.com"]
    start_urls = [f"https://www.elitehubs.com/collections/processors?page={page}"]
    