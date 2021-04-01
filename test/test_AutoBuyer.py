import unittest

from requests.adapters import HTTPAdapter
from urllib3 import Retry

import time as T
from autobuyr.SiteMonitor import SiteMonitor
from autobuyr.Site import Site

from lxml import html
import requests


class TestAutoBuyer(unittest.TestCase):

    def setUp(self):
        self.site = Site("bestbuy")
        self.urls = {
            '3060ti': [
                "https://www.bestbuy.com/site/asus-tuf-rtx3060ti-8gb-gddr6-pci-express-4-0-graphics-card-black/6452573.p?skuId=6452573",
                "https://www.bestbuy.com/site/nvidia-geforce-rtx-3070-8gb-gddr6-pci-express-4-0-graphics-card-dark-platinum-and-black/6429442.p?skuId=6429442",
            ]
        }
        self.rsession = requests.Session()
        retry = Retry(connect=1, backoff_factor=0.5)
        adapter = HTTPAdapter(max_retries=retry)
        self.rsession.mount('http://', adapter)
        self.rsession.mount('https://', adapter)

    def tstart(self):
        self.a_time = T.perf_counter()

    def tstop(self):
        self.b_time = T.perf_counter()
        print(f"Completed in {self.b_time - self.a_time:0.4f}s")

    def test_CheckStockSpeed(self):
        M = SiteMonitor(True, self.urls, False)
        self.site.load_url(self.urls['3060ti'][0], M.driver)
        self.tstart()
        print("WEBDRIVER_TEST:")
        try:
            e = self.site.element_exists(self.site.stat['OutOfStock'], driver=M.driver)
            print(e, type(e))
        except Exception as e:
            print(f"In Stock??? {str(e)}")
        self.tstop()
        M.kill()

    def inStockReq(self, tree):
        instock = tree.xpath(self.site.map[self.site.product_page][0]['p'])
        print("REQUESTS_TEST:", "In Stock." if instock == [] else "Out of Stock.")

    def test_CheckStockSpeedRequests(self):
        headers = {'User-Agent': 'Mozilla/5.0 (platform; rv:geckoversion) Gecko/geckotrail Firefox/firefoxversion',
                   'Connection': 'keep-alive',
                   'Referer': f'{self.site.domain}/',
                   'Accept': '*/*',
                   'Origin': f'{self.site.domain}'}
        page = requests.get(self.urls['3060ti'][0], headers=headers)
        tree = html.fromstring(page.content)
        self.tstart()
        self.inStockReq(tree)
        self.tstop()

    def get_headers(self, url):
        domain = url.split(".com")[0]+".com"
        return [
            # {
            #     'User-Agent': 'Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Googlebot/2.1; +http://www.google.com/bot.html) Chrome/41.0.2272.96 Safari/537.36',
            #     "Cache-Control": "max-age=0",
            #     "Connection": "keep-alive",
            #     "Host": "https://www.google.com/",
            #     'Origin': f'{domain}',
            #     'Referer': f'{domain}/',
            # },
            {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:87.0) Gecko/20100101 Firefox/87.0',
                'Referer': f'{domain}/',
                'Accept': '*/*',
                'Origin': f'{domain}'
            },
            # {
            #     "Accept": '*/*',
            #     "Accept-Encoding": "gzip, deflate, br",
            #     "Accept-Language": "en-US,en;q=0.5",
            #     "Connection": "keep-alive",
            #     "Host": f'{domain}',
            #     "TE": "Trailers",
            #     "Upgrade-Insecure-Requests": "1",
            #     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:87.0) Gecko/20100101 Firefox/87.0"
            # },
        ]

    def test_headers(self):
        urls = ["https://www.officedepot.com/a/products/664011/BIC-Round-Stic-Ballpoint-Pens-Medium/",
                "https://www.bestbuy.com/site/hot-wheels-worldwide-basic-car-styles-may-vary/6151804.p?skuId=6151804",
                "https://www.bhphotovideo.com/c/product/1431041-REG/sandisk_sdsqxa2_064g_g_extreme_microsd_64gb_card.html"]

        for u in urls:
            t = []
            for h in self.get_headers(u):
                p = self.rsession.get(u, headers=h)
                T.sleep(3)
                t.append(p.status_code)
            print(f"{u}: {' '.join([str(_) for _ in t])}")
        self.rsession.close()





    


if __name__ == '__main__':
    unittest.main()
