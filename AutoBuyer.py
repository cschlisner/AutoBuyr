
from reprint import output
import random
import time
import traceback
from datetime import datetime
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.keys import Keys
from Keymap import KeyStr
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

from time import sleep 
import threading 
import sys, os
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

# XPath Crawler -- streamlines webpage traversal
class Site:
    # full domain
    domain = ""
    # how often we should hit the site
    ping = 1
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
            self.ping = sitemap[domain]["PingRate"]
            self.page = sitemap[domain]["Page"]
            self.map = sitemap[domain]["Map"]
            self.layout = sitemap[domain]["Layout"]

    def url(self, i):
        return self.domain+self.page[self.layout[i]]

class CheckoutProc(threading.Thread):
    def __init__(self, driver, ):
        super().__init__(self)




class productMonitor(threading.Thread):  
    AUTO_PURCHASE = False
    PURCHASE_INITIATED=False
    BOUGHT = False
    def __init__(self, driver, urls, auto_buy, debug=False):
        threading.Thread.__init__(self)
        self.AUTO_PURCHASE = auto_buy
        self.driver = driver
        self.driver.start_client()
        self.domain = ''
        self.URL = {}
        for p in urls:
            if self.domain == '':
                self.domain = urls[p][0].split('.')[1]
            for u in urls[p]:
                self.URL[u] = { 
                                'status': False,
                                'info': '',
                                'exc': '',
                                'prod': p
                }
        self.site = Site(self.domain)
        self.stopped = False
        self.debug=debug
        self.driver.get(self.site.domain)


    def inStock(self, url):
        page = list(filter(lambda p: p in self.driver.current_url, self.site.map))[0]
        assert page in url

        try:
            # self.site.map[page][0] will always be the sold out element 
            e = self.driver.find_element_by_xpath(self.site.map[page][0]["p"])
            return e == None
        except NoSuchElementException as e:
            self.info="No Such Element: "+self.site.map[page][0]['p']
            return True

    def alert(self, url, msg, stat=False):
        self.URL[url]['info'] = msg
        self.URL[url]['status'] = stat
        if (self.debug):
            print(msg)
    
    def run(self):
        while self.stopped==False:
            for url in self.URL:
                try:
                    self.alert(url, "Updating...")
                    self.driver.get(url)   
                    # we are on the product page
                    # check stock and attempt checkout
                    if (not self.inStock(url)):
                        self.alert(url, "", False)
                        self.driver.implicitly_wait(self.site.ping)
                        continue
                    else:
                            # in stock now
                            self.alert(url, "Now in stock", True)
                            if self.AUTO_PURCHASE:
                                # Attempting Purchase
                                self.PURCHASE_INITIATED = True
                                try: 
                                    self.URL[url]['exc'] = ""
                                    p = self.attempt_buy(url)
                                    if p:
                                        self.alert(url, "PURCHASED {} for {}".format(self.prodname, self.PURCHASE_TOTAL))
                                        self.kill()
                                        return
                                    else:
                                        self.update()
                                except Exception as e:
                                    # purchase failed
                                    self.PURCHASE_INITIATED = False
                                    self.EXCEPTION = e
                                    exc_type, exc_obj, exc_tb = sys.exc_info()
                                    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                                    self.URL[url]['exc'] = "{}:{} in {} @ {}".format(exc_type, exc_obj, fname, exc_tb.tb_lineno)
                                    with open("log/exc_{}.txt".format(self.domain), "a") as f:
                                        f.write(datetime.now().strftime('%a-%b-%d-%H-%M-%S\n'))
                                        f.write(url)
                                        traceback.print_exc(file=f)
                                        f.write("".join(["-" for i in range(30)]))
                                    self.driver.save_screenshot("scrn/error/{}.png".format(self.domain))
                                    self.driver.delete_all_cookies()
                except Exception as e: 
                    self.EXCEPTION = e
                    with open("log/exc_{}.txt".format(self.domain), "a") as f:
                        f.write(datetime.now().strftime('%a-%b-%d-%H-%M-%S\n'))
                        f.write(url)
                        traceback.print_exc(file=f)
                        f.write("".join(["-" for i in range(30)]))
                    self.kill()

    def kill(self):     
        self.stopped = True
        self.driver.quit()

    def clean(self, url):
        return ''.join(c for c in url if c.isalnum())

    def processElem(self, url, element):
        self.alert(url, "proc({})".format(element["label"]))
        if "blocking" in element:
            for b_e in element["blocking"]:
                self.processElem(url, b_e)

        xpath = element["p"]
        click = "c" in element and element["c"]
        inputText = None if "it" not in element else element["it"]
        expectedText = None if "et" not in element else element["et"]
        
        # element is not expected to be there -- ok if missing or present
        notExpected = "ne" in element and element["ne"]
        # element should not be present -- fail if we detect it
        notPresent = "np" in element and element["np"]

        if "iframe" in element:
            self.driver.switch_to.frame(element["iframe"])

        if "w" in element:
            self.driver.implicitly_wait(element["w"])

        try:
            el = WebDriverWait(self.driver, 1 if (notPresent or notExpected) else 5).until(
                ec.presence_of_element_located((By.XPATH, xpath))
            )
        except Exception as e:
            if notExpected or notPresent:
                return
            else:
                raise e
        
        if notPresent:
            raise Exception("Element {} found when not expected.".format(element["label"]))
            
        #move the mouse back to element if things were blocking it
        if "blocking" in element:
            ac = ActionChains(self.driver)
            ac.move_to_element(el).perform()

        #screenshot if debug
        if self.debug:
            try:
                el.screenshot("scrn/{}-{}.png".format(self.domain,element["label"]))
            except:
                try:
                    self.driver.save_screenshot("scrn/{}-{}-fail.png".format(self.domain,element["label"]))
                except: 
                    raise e


        if inputText is not None:
            if "CI." in inputText:
                inputText = checkout_info[inputText.split(".")[1]]
            elif "Keys." in inputText:
                inputText = KeyStr[input.split(".")[1]]
            if "select[" in element["p"]:
                select = Select(el)
                try:
                    select.select_by_value(inputText)
                except:
                    select.select_by_visible_text(inputText)
            else:
                try:
                    el.clear()
                    el.send_keys(Keys.BACKSPACE)
                except:
                    pass
                
                for k in inputText:
                    el.send_keys(k) 

        if expectedText is not None:
            if element["p"][:7] == "//input" or element["p"][:8]=="//select":
                #check value instead of text content
                assert el.get_attribute('value') == expectedText
            else: assert el.text == expectedText

        if click:
            if element["label"] == "ConfirmOrder":
                if debug:
                    return
                self.alert("ATTEMPTING PURCHASE")
            button = WebDriverWait(self.driver, 10).until(
                ec.element_to_be_clickable((By.XPATH, xpath))
            )
            button.click()


        if element["label"] == "Total":
            self.PURCHASE_TOTAL = el.text 
        
        if "iframe" in element:
            self.driver.switch_to.default_content()

    def attempt_buy(self, url, attempts=1):
        pagei = 0
        retry=attempts
        purchase_complete = False
        while not purchase_complete:
            for page in self.site.map:
                if page in self.driver.current_url:
                    # process elements on our page (in order)
                    for element in self.site.map[page]:
                        try:
                            self.processElem(url, element)
                        except Exception as e:
                            self.alert(url, "Couldn't process {} on {}".format(element["label"], page))
                            raise e
                        if element["label"] == "ConfirmOrder":
                            purchase_complete = True
                            self.driver.save_screenshot("scrn/PurchaseComplete.png")
                            return True
                    if pagei < len(self.site.layout): 
                        self.driver.get(self.site.url(pagei))
                    sleep(2)
                    pagei += 1
            # we are not on a recognized page
            self.driver.save_screenshot("scrn/error/{}.png".format(self.driver.current_url))
            return False


monitor_url = {
    # "officedepot":{
    #     'test': ["https://www.officedepot.com/a/products/321413/Turtles-Original-Bite-Size-Candies-042/"],
        # '3060':["https://www.officedepot.com/a/products/8113849/PNY-GeForce-RTX-3060-12GB-XLR8/"], 
        # '3060ti': ["https://www.officedepot.com/a/products/3973362/PNY-GeForce-RTX-3060-Ti-8GB/", "https://www.officedepot.com/a/products/9801645/PNY-GeForce-RTX-3060-Ti-8GB/"]
    # },
    "bestbuy1":{
        #'test':["https://www.bestbuy.com/site/amd-ryzen-7-3700x-3rd-generation-8-core-16-thread-3-6-ghz-4-4-ghz-max-boost-socket-am4-unlocked-desktop-processor/6356277.p?skuId=6356277"],
        '3060ti': [
            "https://www.bestbuy.com/site/nvidia-geforce-rtx-3060-ti-8gb-gddr6-pci-express-4-0-graphics-card-steel-and-black/6439402.p?skuId=6439402", 
            "https://www.bestbuy.com/site/evga-nvidia-geforce-rtx-3060-ti-ftw3-gaming-8gb-gddr6-pci-express-4-0-graphics-card/6444444.p?skuId=6444444",
            "https://www.bestbuy.com/site/evga-nvidia-geforce-rtx-3060-ti-ftw3-gaming-8gb-gddr6-pci-express-4-0-graphics-card/6444449.p?skuId=6444449",
            ],
    },
    "bestbuy2":{
        '3060ti':[
            "https://www.bestbuy.com/site/asus-tuf-rtx3060ti-8gb-gddr6-pci-express-4-0-graphics-card-black/6452573.p?skuId=6452573",
            "https://www.bestbuy.com/site/nvidia-geforce-rtx-3070-8gb-gddr6-pci-express-4-0-graphics-card-dark-platinum-and-black/6429442.p?skuId=6429442",
        ]
    },
    "bestbuy3":{
        '3060ti':[
            "https://www.bestbuy.com/site/evga-nvidia-geforce-rtx-3060-ti-xc-gaming-8gb-gddr6-pci-express-4-0-graphics-card/6444445.p?skuId=6444445",
            "https://www.bestbuy.com/site/pny-geforce-rtx-3060ti8gb-uprising-dual-fan-graphics-card/6446660.p?skuId=6446660",
        ]
    }
}


debug=False
def init(headless, driver=""):
    if driver == "chrome":
        chromeOptions = webdriver.ChromeOptions()
        chromeOptions.headless = headless
        broswer = webdriver.Chrome(executable_path="./chromedriver.exe", options=chromeOptions)
    elif driver == "phantomjs":
        broswer = webdriver.PhantomJS(executable_path="./phantomjs.exe")
    else: #"firefox"
        fireFoxOptions = webdriver.FirefoxOptions()
        fireFoxOptions.headless = headless
        broswer = webdriver.Firefox(executable_path="./geckodriver.exe", options=fireFoxOptions, service_log_path="gecko.log")
    return broswer

def alert(monitor):
    pass

def col(string, c):
    colors = {
        "header" : '\033[95m',
        "blue" : '\033[94m',
        "green" : '\033[92m',
        "yellow" : '\033[93m',
        "red" : '\033[91m',
        "bold" : '\033[1m',
        "cyan" : '\033[36m',
        "underline" : '\033[4m',
        "ENDC" : '\033[0m',
    }
    return colors[c] + string + colors["ENDC"]

def main():
    debug = False
    headless = True
    if "--debug" in sys.argv:
        debug = True
    if "--gui" in sys.argv:
        headless = False

    if os.path.exists("checkout.json"):
        with open("checkout.json", "r") as f:
            checkout_info = json.load(f)

    urlc = 0
    
    with output(output_type="dict", interval=50) as output_lines:    
        monitors = []
        for site in monitor_url:
            output_lines[site]="starting monitor...."
            monitors.append(productMonitor(init(headless), monitor_url[site], True, debug=debug))
            print(monitors[-1].domain, str(monitors[-1].URL))
            for p in monitor_url[site]:
                urlc += len(monitor_url[site][p])

    for monitor in monitors:
        monitor.start()   
   
    try:
        stoppedc = 0 
        if not debug:
            with output(initial_len=urlc+1, interval=50) as output_lines:
                output_lines[0] = "{}\t\t\t\t|\t\t{}\t\t|\t\t{}|\t\t{}\t\t{}{}".format("Monitor", "Product", "Status", "Info", "Running Threads: ", threading.activeCount())
                while stoppedc < len(monitors):
                    i = 1
                    for m in monitors:
                        for u in m.URL:
                            instock = col("IN STOCK", "green") if m.URL[u]['status'] else col("OUT OF STOCK", "red")
                            output_lines[i] = "{}\t|\t\t{}\t\t|\t\t{}\t\t|\t{}\t|{}".format(m.domain, m.URL[u]['prod'], instock, col(m.URL[u]['info'],"yellow"), m.URL[u]['exc'])
                            if m.URL[u]['status']:
                                alert(m)
                            i += 1
                        if m.stopped: stoppedc += 1
        else:
            while stoppedc < len(monitors):
                stoppedc = 0
                for i, m in enumerate(monitors):
                    if m.stopped: stoppedc += 1
    except (KeyboardInterrupt, Exception) as e:
        traceback.print_exc()
        print("Killing all monitors")
        for m in monitors:
            m.kill()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        exit(0)
        
    