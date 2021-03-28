import os
import pathlib
import sys
import threading
import traceback
from datetime import datetime
from time import sleep

import psutil
import requests
from lxml import html

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait

from Keymap import KeyStr
from Site import Site


class SiteMonitor(threading.Thread):
    AUTO_PURCHASE = False
    BOUGHT = False

    def __init__(self, headless, urls, auto_buy=False, budget=None, debug=False, checkout=None):
        threading.Thread.__init__(self)
        self.purchasing = None
        self.AUTO_PURCHASE = auto_buy
        self.purchase_total = ''
        self.checkout_info = checkout
        self.driver = self.get_web_driver(headless)
        self.driver.start_client()
        self.domain = ''
        # dict of prod(str):price limit(float)
        self.budget = budget
        self.URL = {}
        for p in urls:
            if self.domain == '':
                self.domain = urls[p][0].split('.')[1]
            for u in urls[p]:
                self.URL[u] = {
                    'status': False,
                    'info': '',
                    'price': '',
                    'exc': '',
                    'prod': p
                }
        self.site = Site(self.domain)
        self.driver.get(self.site.domain)
        self.driver.minimize_window()
        self.stopped = False
        self.debug = debug

    @staticmethod
    def get_web_driver(headless, driver=""):
        if driver == "chrome":
            chromeOptions = webdriver.ChromeOptions()
            chromeOptions.headless = headless
            broswer = webdriver.Chrome(executable_path=str(pathlib.Path(__file__).parent.absolute())+"/driver/chromedriver.exe", options=chromeOptions)
        elif driver == "phantomjs":
            broswer = webdriver.PhantomJS(executable_path=str(pathlib.Path(__file__).parent.absolute())+"/driver/phantomjs.exe")
        else:  # "firefox"
            fireFoxOptions = webdriver.FirefoxOptions()
            fireFoxOptions.headless = headless
            broswer = webdriver.Firefox(executable_path=str(pathlib.Path(__file__).parent.absolute())+"/driver/geckodriver.exe", options=fireFoxOptions)
        return broswer

    def in_stock_wd(self, url):
        try:
            # self.site.map[page][0] will always be the sold out element 
            e = self.driver.find_element_by_xpath(self.site.map[self.site.product_page][0]["p"])
            return e == None
        except NoSuchElementException as e:
            self.info = "No Such Element: " + self.site.map[self.site.product_page][0]['p']
            return True

    def in_stock_req(self, url):
        try:
            self.alert(url, "Updating...")
            pricet = None
            page = self.site.load_url(url)
            self.URL[url]['exc'] = ""

            timeout = [] if "Timeout" not in self.site.stat else self.site.element_exists(self.site.stat['Timeout'], tree=page)
            if not timeout:

                outofstock = [] if "OutOfStock" not in self.site.stat else self.site.element_exists(self.site.stat["OutOfStock"], tree=page)
                instock = [0] if "InStock" not in self.site.stat else self.site.element_exists(self.site.stat["InStock"], tree=page)
                price = [] if "Price" not in self.site.stat else self.site.element_exists(self.site.stat["Price"], tree=page)

                in_stock = instock and not outofstock

                pricet = None if not price else self.site.get_element_text(price[0])
                self.alert(url, f"{url if in_stock else ''}", in_stock, price=pricet)

                # IN STOCK AND SET TO PURCHASE
                if self.purchasing is None and in_stock:
                    self.driver.get(url)
                    self.driver.save_screenshot(f"scrn/{self.domain}-{self.URL[url]['prod']}-INSTOCK.png")
                    if self.AUTO_PURCHASE and self.price_check(url):
                        # self.alert(url, "Now in stock", True)
                        self.purchasing = url
                        try:
                            self.URL[url]['exc'] = ""
                            p = self.attempt_buy(url)
                            if p:
                                self.BOUGHT = True,
                                self.alert(url, "PURCHASED {} for {}".format(self.URL[url]['prod'], self.purchase_total))
                                self.kill()
                                return False
                            else:
                                self.alert(url, "Purchase Failed", False)
                                self.purchasing = None
                                self.driver.minimize_window()
                                self.driver.delete_all_cookies()
                                return False
                        except Exception as e:
                            # purchase failed
                            exc_type, exc_obj, exc_tb = sys.exc_info()
                            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                            with open("log/exc_{}.txt".format(self.domain), "a") as f:
                                f.write(datetime.now().strftime('%a-%b-%d-%H-%M-%S\n'))
                                f.write(url+"\n")
                                f.write(f"Err: {self.URL[url]['exc']}\n")
                                traceback.print_exc(file=f)
                                f.write("".join(["-" for i in range(30)]))

                            self.alert(url, "Purchase Failed", False)
                            self.purchasing = None
                            self.URL[url]['exc'] = "{}:{} in {} @ {}".format(exc_type, exc_obj, fname,
                                                                             exc_tb.tb_lineno)
                            self.driver.save_screenshot("scrn/error/{}.png".format(self.domain))
                            self.driver.minimize_window()
                            self.driver.delete_all_cookies()
            else:
                self.err(url, "Saw Timeout Element")
            return False
        except Exception as e:
            self.err(url, f"{str(e)} : {sys.exc_info()[0]}")
            with open("log/exc_{}.txt".format(self.domain), "a") as f:
                f.write(datetime.now().strftime('%a-%b-%d-%H-%M-%S\n'))
                f.write(url)
                traceback.print_exc(file=f)
                f.write("".join(["-" for i in range(30)]))

    def alert(self, url, msg, stat=None, price=None):
        self.URL[url]['info'] = msg
        self.URL[url]['status'] = self.URL[url]['status'] if stat is None else stat
        self.URL[url]['price'] = str(price) if price is not None else self.URL[url]['price']
        if self.debug:
            print(msg)

    def err(self, url, msg):
        self.URL[url]['exc'] = msg
        self.URL[url]['status'] = False
        self.URL[url]['info'] = ""
        if self.debug:
            print(msg)

    def price_check(self, url):
        try:
            return self.budget is not None and float(self.clean_price(self.URL[url]['price'])) <= self.budget[
                self.URL[url]['prod']]
        except:
            return False

    def run(self):
        while not self.stopped and not self.BOUGHT:
            try:
                sleep(self.site.ping)
                urlThreads = []
                for url in self.URL:
                    self.URL[url]['exc'] = ""
                    urlt = threading.Thread(target=self.in_stock_req, args=(url,))
                    urlThreads.append(urlt)
                    urlt.start()

                for t in urlThreads:
                    t.join()
                    if self.stopped:
                        return

            except Exception as e:
                with open("log/exc_{}.txt".format(self.domain), "a") as f:
                    f.write(datetime.now().strftime('%a-%b-%d-%H-%M-%S\n'))
                    traceback.print_exc(file=f)
                    f.write("".join(["-" for i in range(30)]))
                self.kill()

    def kill(self):
        self.stopped = True
        print(f"Killing Monitor {self.domain}")

        # if self.driver.firefox_binary:
        #     print(f"killing binary({self.domain})")
        #     self.driver.firefox_binary.kill()

        # none of the api methods work so...
        # self.driver.quit()
        self.driver.close()
        # self.driver.stop_client()
        # self.driver.service.stop()
        # print(f"({self.domain}) killing parent: {p.parent().pid} {p.parent().as_dict()}")
        # print(f"({self.domain}) killing pid {p.pid} with parent: {p.parent().pid} {p.parent().as_dict()}")
        # p.terminate()
        # print(os.system(f"taskkill /F /PID {p.parent().pid}"))
        # print(os.system(f"taskkill /F /PID {self.driver.service.process.pid}"))
        print(f"Monitor {self.domain} quit successfully?")

    @staticmethod
    def clean_price(price):
        return ''.join(c for c in price if c.isnumeric() or c == '.')

    def process_elem(self, url, element):
        self.alert(url, "proc({})".format(element["label"]))
        ac = ActionChains(self.driver)
        if "blocking" in element:
            for b_e in element["blocking"]:
                self.process_elem(url, b_e)

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
            sleep(element["w"])

        try:
            if click or inputText:
                el = self.site.element_exists(element, driver=self.driver, timeout=1 if (notPresent or notExpected) else 5)
                try:
                    ac.move_to_element(el).perform()
                except:
                    pass
            else:
                el = self.site.element_exists(element, tree=html.fromstring(self.driver.page_source))
                assert el
        except Exception as e:
            if notExpected or notPresent:
                return
            else:
                raise Exception(element['label'], sys.exc_info()[0])

        if notPresent:
            raise Exception("Element {} found when not expected.".format(element["label"]))


        # screenshot if debug
        if self.debug:
            try:
                el.screenshot("scrn/{}-{}.png".format(self.domain, element["label"]))
            except:
                self.driver.save_screenshot("scrn/{}-{}-fail.png".format(self.domain, element["label"]))

        if inputText is not None:
            if "CI." in inputText:
                inputText = self.checkout_info[inputText.split(".")[1]]
            elif "Keys." in inputText:
                inputText = KeyStr[inputText.split(".")[1]]
            if "select[" in element["p"]:
                select = Select(el)
                try:
                    select.select_by_value(inputText)
                except Exception:
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
            assert self.site.get_element_text(el) == expectedText

        if click:
            if element["label"] == "ConfirmOrder":
                if self.debug:
                    return
                self.alert(url, "ATTEMPTING PURCHASE")
            WebDriverWait(self.driver, 30).until(
                ec.element_to_be_clickable((By.XPATH, xpath))
            )
            el.click()

        if element["label"] == "Total":
            self.purchase_total = self.site.get_element_text(el)

        if "iframe" in element:
            self.driver.switch_to.default_content()

    # should be on url already
    def attempt_buy(self, url, attempts=1):
        self.driver.maximize_window()
        pagei = 0
        retry = attempts
        purchase_complete = False
        while not purchase_complete:
            for page in self.site.map:
                if page in self.driver.current_url:
                    # process elements on our page (in order)
                    for element in self.site.map[page]:
                        try:
                            self.process_elem(url, element)
                        except Exception as e:
                            self.err(url, f"Couldn't process {element['label']} on {page}")
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
