import json 

# XPath Crawler -- streamlines webpage traversal
import pathlib

import requests

from lxml import html
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.firefox.webelement import FirefoxWebElement


class Site:
    # full domain
    domain = ""
    # how often we should hit the site
    ping = 1
    # Site pages for nav
    pages = {}
    # Site map
    map = {}
    # Status Elements
    stat = {}
    # Site layout for checkout process (page order after product is added to cart)
    layout = []
    # Product Page Key
    product_page = ''

    def __init__(self, domain, sitemap_file=str(pathlib.Path(__file__).parent.absolute())+"/PATH/sitemap.json"):
        self.domain = domain
        with open(sitemap_file, "r") as f:
            sitemap = json.load(f)
            self.domain = sitemap[domain]["Domain"]
            self.ping = sitemap[domain]["PingRate"]
            self.page = sitemap[domain]["Page"]
            self.stat = sitemap[domain]["StatusElem"]
            self.map = sitemap[domain]["Map"]
            self.layout = sitemap[domain]["Layout"]
        self.product_page = [p for p in self.map if self.map[p][0]['label']=="OutOfStock"][0]

    """
    return current page as lxml etree for url, using browser or request (faster) if no driver is supplied
    """
    def load_url(self, url, driver=None):
        if not driver:
            headers = {'User-Agent': 'Mozilla/5.0 (platform; rv:geckoversion) Gecko/geckotrail Firefox/firefoxversion',
                       'Connection': 'keep-alive',
                       'Referer': f'{self.domain}/',
                       'Accept': '*/*',
                       'Origin': f'{self.domain}'}
            page = requests.get(url, headers=headers, timeout=2)
            if page.ok:
                tree = html.fromstring(page.content)
            else:
                raise Exception(f"{str(page.status_code)} on request.")
        else:
            driver.get(url)
            tree = html.fromstring(driver.page_source)
        return tree

    """
    Check if element is present using webdriver if one is supplied or html
    throws timeout exceptions for driver calls
    element: json element containing at least ['p']:"<xpath>" 
    """
    def element_exists(self, element, driver=None, tree=None, timeout=3):
        if driver:
            return WebDriverWait(driver, timeout).until(
                ec.presence_of_element_located((By.XPATH, element["p"]))
            )
        elif html:
            e = tree.xpath(element["p"])
            return None if e==[] else e[0]

    """"
    figures out what type of html element you have and gets the text from it. 
    depending on return from element_exists, element could be lxml.html.HtmlElement or selenium webelement
    """
    def get_element_text(self, element):
        if type(element) == html.HtmlElement:
            t = element.text
            tc = element.text_content()
            v = element.get('value')
            return t if t else tc if tc else v
        elif type(element) == FirefoxWebElement:
            if element.tag_name in ["input", "select"]:
                return element.get_attribute('value')
            else:
                return element.text

    """
    get next url in navigation list (e.g. site.url(0) = "https://www.domain.com/cart/", site.url(2)="https://www.domain.com/checkout/")
    """
    def url(self, i):
        return self.domain+self.page[self.layout[i]]


