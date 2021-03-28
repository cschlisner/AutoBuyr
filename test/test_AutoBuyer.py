import unittest
import AutoBuyer as ab
import time as T
from SiteMonitor import SiteMonitor
from Site import Site

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


if __name__ == '__main__':
    unittest.main()
