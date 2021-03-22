from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
from time import sleep 
import threading 


# XPath Crawler -- streamlines webpage traversal
class XPathC:
    _SoldOutDict = {
        "bestbuy": ("//button[@class='btn btn-disabled btn-lg btn-block add-to-cart-button']", lambda e: e.text=="Sold Out"), 
        "officedepot": ("//div[@class='deliveryMessage']/span", lambda e: e.text=="Out of stock for delivery"),
        "amazon": ("/html/body/div[2]/div[2]/div[9]/div[3]/div[4]/div[19]/div[1]/span", lambda e: e.text=="Currently unavailable.")
    }

    _CheckoutPaths = {
        "bestbuy" : [("//button[contains(@class,'add-to-cart-button')]", lambda e: e.send_keys(Keys.ENTER), 2), # add to cart
                    ("href:/cart", None, 4), # go to cart
                    ("//select[contains(@id, 'quantity')]", lambda e: e.send_keys("1"), 3), # make sure we only added one to cart
                    ("/html/body/div[1]/main/div/div[2]/div[1]/div/div[1]/div[1]/section[2]/div/div/div[3]/div/div[1]/button", lambda e: e.click(), 4), # checkout
                    ("//button[contains(@class, 'continue guest')]", lambda e: e.click(),3), #continue as guest 
                    # Checkout Info Fields
                    ("//input[@id='consolidatedAddresses.ui_address_2.firstName']", lambda e: sendAllKeys(e, checkout_info['FName']),2), 
                    ("//input[@id='consolidatedAddresses.ui_address_2.lastName']", lambda e: sendAllKeys(e, checkout_info['LName']),2), 
                    ("//input[@id='consolidatedAddresses.ui_address_2.street']", lambda e: sendAllKeys(e, checkout_info['Addr']),2), 
                    ("//input[@id='consolidatedAddresses.ui_address_2.city']", lambda e: sendAllKeys(e, checkout_info['City']),2), 
                    ("//select[@id='consolidatedAddresses.ui_address_2.state']", lambda e: [e.send_keys(Keys.DOWN) for k in range(9)],2), 
                    ("//input[@id='consolidatedAddresses.ui_address_2.zipcode']", lambda e: sendAllKeys(e, checkout_info['ZIP']),2), 
                    ("//input[@id='user.emailAddress']", lambda e: sendAllKeys(e, checkout_info['Email'])), 
                    ("//input[@id='user.phone']", lambda e: sendAllKeys(e, checkout_info['Phone'])), 
                    ("/html/body/div[1]/div[2]/div/div[2]/div[1]/div[1]/main/div[2]/div[2]/form/section/div/div[2]/div/div/button", lambda e: e.click())
        ],
        "officedepot": [("//input[@id='addToCartButtonId']", lambda e: e.click(), 3), 
                        ("href:/cart/shoppingCart.do",None,4),
                        ("//input[@id='quantity0']", lambda e: e.clear(), 1),
                        ("//input[@id='quantity0']", lambda e: e.send_keys("1"), 1),
                        ("//a[contains(@class,'checkout-btn')]", lambda e: e.click(), 3),
                        ("/html/body/div[3]/div[3]/div/div/div/div[1]/div/div/div/div[2]/div/a", lambda e: e.click(), 3),
                        #checkout info
                        ("//input[@id='firstName-2']", lambda e: sendAllKeys(e, checkout_info['FName']),2), 
                        ("//input[@id='lastName-2']", lambda e: sendAllKeys(e, checkout_info['LName']),2), 
                        ("//input[@id='address1-2']", lambda e: sendAllKeys(e, checkout_info['Addr']),2), 
                        ("//input[@id='postalCode1-2']", lambda e: sendAllKeys(e, checkout_info['ZIP']),2), 
                        ("//input[@id='city-2']", lambda e: sendAllKeys(e, checkout_info['City']),2), 
                        ("//select[@id='state-2']", lambda e: [e.send_keys(Keys.DOWN) for k in range(5)],2), 
                        ("//input[@id='email-2']", lambda e: sendAllKeys(e, checkout_info['Email'])), 
                        ("//input[@id='phoneNumber1-2']", lambda e: sendAllKeys(e, checkout_info['Phone'][:3])), 
                        ("//input[@id='phoneNumber2-2']", lambda e: sendAllKeys(e, checkout_info['Phone'][3:6])), 
                        ("//input[@id='phoneNumber3-2']", lambda e: sendAllKeys(e, checkout_info['Phone'][6:10])), 
                        ("/html/body/div[1]/div[2]/div/div[2]/div[1]/div[1]/main/div[2]/div[2]/form/section/div/div[2]/div/div/button", lambda e: e.click())
        ]
    }

    def sendAllKeys(self, element, text):
        for k in checkout_info['Email']:
            element.send_keys(k) 

    domain = ""

    # SO = the sold out element. 
    # SO[0] = xpath
    # SO[1] = lambda indicating whether or not element matching xpath matches expected condition
    # SO[1](driver.find_element_by_xpath(SO[0])) == True <=> product is sold out
    SO = None

    # list of tuples (xpath, lambda, ?wait) where lambda does something with the found element, and wait is an optional delay between steps
    # p[0..n] = checkout traversal. p[i](driver.find_element_by_xpath(p[i])) advances the checkout process one step. 
    p = []

    def __init__(self, domain):
        self.domain = domain
        self.SO = self._SoldOutDict[domain]
        self.p = self._CheckoutPaths[domain]


class productMonitor(threading.Thread):    
    info = ""
    status = 0
    URL = ""
    domain = ""
    driver = None
    name = ""
    xpathc = None
    update_int = 1
    autobuy = False
    BOUGHT = False
    def __init__(self, name, url, update_freq, auto_buy, headless=True):
        threading.Thread.__init__(self)
        self.name = name
        self.URL = url
        self.domain = url.split('.')[1]
        self.driver = init(headless)
        self.xpathc = XPathC(self.domain)
        self.update_int = update_freq
        self.autobuy = auto_buy
        self.stopped = False
        self.driver.get(url)
        sleep(8)


    def inStock(self):
        try:
            el = self.driver.find_element_by_xpath(self.xpathc.SO[0])
            return not self.xpathc.SO[1](el)
        except NoSuchElementException:
            self.info="No Such Element: "+self.xpathc.SO[0]
            return True

    def update(self):
        self.driver.get(self.URL)
    
    def run(self):
        while self.stopped==False:
            try:
                if (self.inStock()):
                    self.alert(self.name+" in stock @ "+self.URL, 1)
                    if self.autobuy:
                        self.buy()
                else: self.info = ""
                sleep(self.update_int)
                self.update()
            except Exception as e: 
                self.info = str(e)
                self.update()
    
    def kill(self):
        self.stopped = True
    
    def alert(self, msg, stat):
        self.info = msg
        self.status = stat

    def buy(self):
        for e in self.xpathc.p:
            try: 
                if "href:" not in e[0]:
                    e[1](self.driver.find_element_by_xpath(e[0]))
                else:
                    self.driver.get("https://www.{}.com{}".format(self.domain, e[0].split(":")[1]))
                if len(e) > 2:
                    sleep(e[2])
            except NoSuchElementException:
                self.info="No Such Element: "+e[0]
                return
        self.autobuy = False
        self.alert("BOUGHT {} @ {} for {}".format(self.name, self.URL, "price"), 0)
        self.BOUGHT = True
        self.stopped = True

            
def init(headless):
    fireFoxOptions = webdriver.FirefoxOptions()
    if headless:
        fireFoxOptions.set_headless()
    broswer = webdriver.Firefox(options=fireFoxOptions)
    return broswer



products = {
    'Test': ["https://www.bestbuy.com/site/whirlpool-5-1-cu-ft-freestanding-gas-range-stainless-steel/4146081.p?skuId=4146081", "https://www.officedepot.com/a/products/434207/HP-950XL951-BlackCyanMagentaYellow-Ink-Cartridges-C2P01FNM/?cm_cat=513382"],
    '3060ti': ["https://www.bestbuy.com/site/nvidia-geforce-rtx-3060-ti-8gb-gddr6-pci-express-4-0-graphics-card-steel-and-black/6439402.p?skuId=6439402", "https://www.bestbuy.com/site/evga-nvidia-geforce-rtx-3060-ti-ftw3-gaming-8gb-gddr6-pci-express-4-0-graphics-card/6444444.p?skuId=6444444", "https://www.officedepot.com/a/products/3973362/PNY-GeForce-RTX-3060-Ti-8GB"],
    '3060':["https://www.officedepot.com/a/products/8113849/PNY-GeForce-RTX-3060-12GB-XLR8/", ]
}

from reprint import output
import random
import time
if __name__ == '__main__':
    monitors = []
    for prod in products:
        for page in products[prod]:
            monitors.append(productMonitor(prod, page, 3, False))
    for monitor in monitors:
        monitor.start()   
    stoppedc = 0 
    with output(initial_len=len(monitors)+1, interval=0) as output_lines:
        while stoppedc < len(monitors):
            output_lines[0] = "{}\t|\t{}\t|\t{}{}".format("Product", "In Stock", "Running Threads: ", threading.activeCount())
            for i, m in enumerate(monitors):
                output_lines[i+1] = "{}({})\t|\t{}\t|\t{}".format(m.name, m.domain, bool(m.status), m.info)
                if m.stopped: stoppedc += 1
            
        
    