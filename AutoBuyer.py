from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
import selenium_util as Sel
from time import sleep 
import threading 
import json

checkout_info = {
    "CC" : "4111111111111111111",
    "CVV": "123",
    "EXPM": "08",
    "EXPY": "2021",
    "FName" : "FName", 
    "LName" : "Lname",
    "Addr": "123 Main St",
    "State": "CO",
    "City": "Denver",
    "ZIP":"80103",
    "Phone":"1234567891",
    "Phone1":"123",
    "Phone2":"456",
    "Phone3":"7891",
    "Email":"e@mail.com"
}

# because element.send_keys() is broken?
def sendAllKeys(element, text):
        for k in text:
            element.send_keys(k) 

# XPath Crawler -- streamlines webpage traversal
class Site:
    # full domain
    domain = ""
    # Site pages for nav
    pages = {}
    # Site map
    map = {}
    # Site layout (page order)
    layout = []
    
    def __init__(self, domain, sitemap_file="./PATH/sitemap.json"):
        self.domain = domain
        with open(sitemap_file, "r") as f:
            sitemap = json.load(f)
            self.domain = sitemap[domain]["Domain"]
            self.page = sitemap[domain]["Page"]
            self.map = sitemap[domain]["Map"]
            self.layout = sitemap[domain]["Layout"]

    def url(self, i):
        return self.domain+self.page[self.layout[i]]

    

class productMonitor(threading.Thread):    
    info = ""
    status = False
    URL = ""
    domain = ""
    driver = None
    prodname = ""
    site = None
    update_int = 1
    AUTO_PURCHASE = False
    PURCHASE_INITIATED=False
    BOUGHT = False
    EXCEPTION = None
    def __init__(self, product_name, url, update_freq, auto_buy, headless=True):
        threading.Thread.__init__(self)
        self.prodname = product_name
        self.URL = url
        self.domain = url.split('.')[1]
        self.driver = init(headless)
        self.site = Site(self.domain)
        self.update_int = update_freq
        self.AUTO_PURCHASE = auto_buy
        self.stopped = False
        self.driver.get(url)
    

    def inStock(self):
        page = list(filter(lambda p: p in self.driver.current_url, self.site.map))[0]
        assert page in self.URL

        try:
            # self.site.map[page][0] will always be the sold out element 
            e = self.driver.find_element_by_xpath(self.site.map[page][0]["p"])
            return e == None
        except NoSuchElementException as e:
            self.info="No Such Element: "+self.site.map[page][0]['p']
            return True

    def update(self):
        self.driver.get(self.URL)
    
    def run(self):
        while self.stopped==False:
            try:
                # get current url
                loc = self.driver.current_url
                for page in self.site.map:
                    if page in self.URL:
                        # we are on the product page
                        # check stock and attempt checkout
                        while (not self.inStock()):
                            self.status = False
                            self.info = ""
                            sleep(self.update_int)
                            self.update()

                        # in stock now
                        # self.alert(self.name+" in stock @ "+self.URL, True)
                        if self.AUTO_PURCHASE:

                            # Attempting Purchase
                            self.PURCHASE_INITIATED = True
                            try: 
                                self.attempt_buy()
                            except Exception as e:
                                self.PURCHASE_INITIATED = False
                                self.EXCEPTION = e
                                self.kill()
            except Exception as e: 
                self.EXCEPTION = e
                self.kill()
    
    def kill(self):
        self.stopped = True
    
    def alert(self, msg, stat):
        self.info = msg
        self.status = stat

    def processElem(self, element):
        xpath = element["p"]
        click = "c" in element and element["c"]
        inputText = None if "it" not in element else element["it"]
        expectedText = None if "et" not in element else element["et"]
        notPresent = "np" in element and element["np"]

        if "iframe" in element:
            self.driver.switch_to.frame(element["iframe"])

        if "w" in element:
            self.driver.implicitly_wait(element["w"])
        try:
            el = Sel.wait_for_element_by_xpath(self.driver, xpath, 1 if notPresent else 30)
            # el = self.driver.find_element_by_xpath(xpath) 
        except Exception as e:
            if notPresent:
                return
            else:
                raise e
        if inputText is not None:
            if "CI" in inputText:
                inputText = checkout_info[inputText.split(".")[1]]
            if "select[" in element["p"]:
                select = Select(el)
                try:
                    select.select_by_value(inputText)
                except:
                    select.select_by_visible_text(inputText)
            else:
                try:
                    el.clear()
                except:
                    pass
                el.send_keys(inputText)
        if expectedText is not None:
            if element["p"][:7] == "//input":
                #check value instead of text content
                assert el.get_attribute('value') == expectedText
            else: assert el.text == expectedText
        if click:
            Sel.button_click_using_xpath(self.driver,xpath)
        
        if "iframe" in element:
            self.driver.switch_to.default_content()

    def attempt_buy(self):
        pagei = 0
        purchase_complete = False
        # Out of stock should be gone

        while not purchase_complete:
            for page in self.site.map:
                if page in self.driver.current_url:
                    # process elements on our page (in order)
                    for element in self.site.map[page]:
                        print("processing {}".format(element['label']))
                        self.processElem(element)
                        if element["label"] == "ConfirmOrder":
                            purchase_complete = True
                    self.driver.get(self.site.url(pagei))
                    sleep(2)
                    pagei += 1


            
def init(headless):
    fireFoxOptions = webdriver.FirefoxOptions()
    if headless:
        fireFoxOptions.set_headless()
    broswer = webdriver.Firefox(options=fireFoxOptions)
    return broswer



products = {
    'TestOD': ["https://www.officedepot.com/a/products/690690/WorkPro-Quantum-9000-Mesh-Series-High/"],
    # 'TestBB': ["https://www.bestbuy.com/site/whirlpool-5-1-cu-ft-freestanding-gas-range-stainless-steel/4146081.p?skuId=4146081"],
    #'3060ti': ["https://www.bestbuy.com/site/nvidia-geforce-rtx-3060-ti-8gb-gddr6-pci-express-4-0-graphics-card-steel-and-black/6439402.p?skuId=6439402", "https://www.bestbuy.com/site/evga-nvidia-geforce-rtx-3060-ti-ftw3-gaming-8gb-gddr6-pci-express-4-0-graphics-card/6444444.p?skuId=6444444", "https://www.officedepot.com/a/products/3973362/PNY-GeForce-RTX-3060-Ti-8GB"],
    #'3060':["https://www.officedepot.com/a/products/8113849/PNY-GeForce-RTX-3060-12GB-XLR8/", ]
}

def alert(monitor):
    pass


from reprint import output
import random
import time
import traceback
if __name__ == '__main__':
    monitors = []
    for prod in products:
        for page in products[prod]:
            monitors.append(productMonitor(prod, page, 3, True, headless=False))
    for monitor in monitors:
        monitor.start()   
    stoppedc = 0 
    # with output(initial_len=len(monitors)+1, interval=50) as output_lines:
    while stoppedc < len(monitors):
            # output_lines[0] = "{}\t|\t{}\t|\t{}{}".format("Product", "In Stock", "Running Threads: ", threading.activeCount())
        for i, m in enumerate(monitors):
            # output_lines[i+1] = "{}({})\t|\t{}\t|\t{}".format(m.name, m.domain, m.status, m.info)
            if m.status:
                alert(m)
            if m.stopped: stoppedc += 1
            if m.EXCEPTION is not None:
                print("\n\n")
                traceback.print_exception(type(m.EXCEPTION), m.EXCEPTION, m.EXCEPTION.__traceback__)

        
    