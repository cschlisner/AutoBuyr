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
    def __init__(self, headless, urls, auto_buy=False, budget=None, debug=False, checkout=None):
        threading.Thread.__init__(self)
        self.purchasing = None
        self.AUTO_PURCHASE = auto_buy
        self.BOUGHT = None
        self.STATUS = ""
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
                    'prod': p,
                    'purchasing':False,
                    'in_budget':False
                }
        self.site = Site(self.domain)
        self.driver.minimize_window()
        self.stopped = threading.Event()
        self.exited = False
        self.debug = debug

    @staticmethod
    def get_web_driver(headless, driver=""):
        if sys.platform == 'win32':
            if driver == "chrome":
                chromeOptions = webdriver.ChromeOptions()
                chromeOptions.headless = headless
                broswer = webdriver.Chrome(
                    executable_path=str(pathlib.Path(__file__).parent.absolute()) + "/driver/chromedriver.exe",
                    options=chromeOptions)
            elif driver == "phantomjs":
                broswer = webdriver.PhantomJS(
                    executable_path=str(pathlib.Path(__file__).parent.absolute()) + "/driver/phantomjs.exe")
            else:  # "firefox"
                fireFoxOptions = webdriver.FirefoxOptions()
                fireFoxOptions.headless = headless
                broswer = webdriver.Firefox(
                    executable_path=str(pathlib.Path(__file__).parent.absolute()) + "/driver/geckodriver.exe",
                    options=fireFoxOptions)
        else:
            fireFoxOptions = webdriver.FirefoxOptions()
            fireFoxOptions.headless = headless
            broswer = webdriver.Firefox(
                executable_path=str(pathlib.Path(__file__).parent.absolute()) + "/driver/geckodriver-linux",
                options=fireFoxOptions)
        return broswer

    def in_stock_req(self, url):
        try:
            self.alert(url, "/")
            pricet = None
            page = self.site.load_url(url)
            self.alert(url, "-")

            self.URL[url]['exc'] = ""

            timeout = [] if "Timeout" not in self.site.stat else self.site.element_exists(self.site.stat['Timeout'],
                                                                                          tree=page)
            if not timeout:

                outofstock = None if "OutOfStock" not in self.site.stat else self.site.element_exists(
                    self.site.stat["OutOfStock"], tree=page)
                instock = None if "InStock" not in self.site.stat else self.site.element_exists(
                    self.site.stat["InStock"], tree=page)
                price = None if "Price" not in self.site.stat else self.site.element_exists(self.site.stat["Price"],
                                                                                            tree=page)
                pricet = None if price is None else self.site.get_element_text(price)
                in_stock = (instock is not None) and (outofstock is None)
                # self.alert(url,
                #            f"{outofstock}{instock}{price}{in_stock}.{price.text}{price.text_content()}{price.get('value')}=>{pricet}({self.site.get_element_text(price)}")

                self.alert(url, url if in_stock else '\\', in_stock, price=pricet)
                self.price_check(url)

                # IN STOCK AND SET TO PURCHASE
                if self.purchasing is None and in_stock and "purchased" not in self.URL[url]:
                    self.driver.get(url)
                    self.driver.save_screenshot(f"scrn/{self.domain}-{self.URL[url]['prod']}-INSTOCK.png")
                    if self.AUTO_PURCHASE and self.price_check(url):
                        # self.alert(url, "Now in stock", True)
                        self.purchasing = url
                        for queued in self.URL:
                            self.alert(queued, f"Waiting on {url}")
                        try:
                            self.URL[url]['exc'] = ""
                            self.URL[url]['purchasing']=True
                            p = self.attempt_buy(url)
                            if p:
                                self.BOUGHT = url
                                self.URL[url]['purchased']=self.purchase_total
                                self.URL[url]['purchasing'] = False
                                self.alert(url,
                                           "PURCHASED {} for {}".format(self.URL[url]['prod'], self.purchase_total))
                                print('\a')

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
                                f.write(url + "\n")
                                f.write(f"Err: {self.URL[url]['exc']}\n")
                                traceback.print_exc(file=f)
                                f.write("".join(["-" for i in range(30)]))

                            self.alert(url, "Purchase Failed")
                            self.purchasing = None
                            self.URL[url]['purchasing'] = False

                            self.URL[url]['exc'] = "{}:{} in {} @ {}".format(exc_type, exc_obj, fname,
                                                                             exc_tb.tb_lineno)
                            self.driver.save_screenshot("scrn/error/{}.png".format(self.domain))
                            try:
                                with open("scrn/error/{}_pagedump.txt".format(self.domain), "w") as f:
                                    f.write(self.driver.page_source)
                            except:
                                pass
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

    def purchase_alert(self, prod):
        pass

    def alert(self, url, msg=None, stat=None, price=None):
        self.URL[url]['info'] = msg if msg else self.URL[url]['info']
        self.URL[url]['status'] = stat if stat else self.URL[url]['status']
        self.URL[url]['price'] = str(price) if price else self.URL[url]['price']
        self.URL[url]['exc']=""
        if self.debug:
            print(msg)

    def err(self, url, msg):
        self.URL[url]['exc'] = msg
        self.URL[url]['status'] = False
        if self.debug:
            print(msg)

    def price_check(self, url):
        try:
            if self.budget is not None and float(self.clean_price(self.URL[url]['price'])) <= self.budget[self.URL[url]['prod']]:
                self.URL[url]['in_budget']=True
                return self.URL[url]['in_budget']
        except:
            return False

    def run(self):
        while not self.stopped.is_set():
            self.STATUS = "Running."
            try:
                if self.BOUGHT:
                    # remove purchased url from our list to check
                    self.purchase_alert(self.URL[self.BOUGHT])
                    self.BOUGHT = None

                sleep(self.site.ping)
                urlThreads = []
                for url in self.URL:
                    self.URL[url]['exc'] = ""
                    if "purchased" not in self.URL[url]:
                        self.alert(url, "|")
                        urlt = threading.Thread(target=self.in_stock_req, args=(url,))
                        urlThreads.append((url,urlt))
                        urlt.start()

                for t in urlThreads:
                    t[1].join()
                    if "purchased" not in self.URL[t[0]]:
                        self.alert(t[0],"*")

            except Exception as e:
                with open("log/exc_{}.txt".format(self.domain), "a") as f:
                    f.write(datetime.now().strftime('%a-%b-%d-%H-%M-%S\n'))
                    traceback.print_exc(file=f)
                    f.write("".join(["-" for i in range(30)]))

        ## thread stopped
        for u in self.URL:
            self.alert(u, "Stopped.")
            self.err(u,"")

        # if self.driver.firefox_binary:
        #     print(f"killing binary({self.domain})")
        #     self.driver.firefox_binary.kill()

        # none of the api methods work so...
        # self.driver.quit()
        # self.driver.stop_client()
        # self.driver.service.stop()
        # print(f"({self.domain}) killing parent: {p.parent().pid} {p.parent().as_dict()}")
        # print(f"({self.domain}) killing pid {p.pid} with parent: {p.parent().pid} {p.parent().as_dict()}")
        # p.terminate()
        # print(os.system(f"taskkill /F /PID {p.parent().pid}"))
        # print(os.system(f"taskkill /F /PID {self.driver.service.process.pid}"))
        self.STATUS = f"({self.domain}) Attempting to stop service: {self.driver.service} PID {self.driver.service.process.pid}"
        try:
            self.driver.service.stop()
        except:
            self.STATUS = f"({self.domain}) service stop failed -- {sys.exc_info()[0]} Attempting to close browser {self.driver}"
            try:
                self.driver.close()
            except:
                self.STATUS = f"({self.domain}) closing browser failed -- {sys.exc_info()[0]} Attempting to quit browser {self.driver}"
                try:
                    self.driver.quit()
                except:
                    self.STATUS = f"({self.domain}) driver close failed -- fuck it\n{os.system('taskkill /F /IM Firefox.exe')}"
                    sys.exit()
        for u in self.URL:
            self.alert(u, "MONITOR DEAD")
        self.STATUS = f"Monitor {self.domain} quit successfully?"
        self.exited = True

    def kill(self):
        self.STATUS = "Killed."
        self.stopped.set()

    @staticmethod
    def clean_price(price):
        return ''.join(c for c in price if c.isnumeric() or c == '.')

    def process_elem(self, url, element):
        if "blocking" in element:
            for b_e in element["blocking"]:
                self.process_elem(url, b_e)
        self.alert(url, "proc({})".format(element["label"]))
        ac = ActionChains(self.driver)

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

        if "sleep" in element:
            sleep(element["sleep"])

        try:
            # if the element is dynamic or we need to interact with it, use driver wait
            if click or inputText or "w" in element:
                w = 0 if "w" not in element else element['w']
                el = self.site.element_exists(element, driver=self.driver,
                                              timeout=(1 if (notPresent or notExpected) else 5)+w)
                try:
                    ac.move_to_element(el).perform()
                except:
                    pass
            else:  # otherwise we can just find it in the page source quicker
                el = self.site.element_exists(element, tree=html.fromstring(self.driver.page_source))
                if el is None:
                    raise AssertionError(el)
        except Exception as e:
            if notExpected or notPresent:
                return
            else:
                raise Exception(element['label'], (sys.exc_info()[0],sys.exc_info()[1]))

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
            el.send_keys(KeyStr['TAB'])
            sleep(1)

        if expectedText is not None:

            if self.site.get_element_text(el) != expectedText:
                raise AssertionError(self.site.get_element_text(el), expectedText)

        if element["label"] == "Total":
            self.purchase_total = self.site.get_element_text(el)

        if click:
            if element["label"] == "ConfirmOrder":
                if self.debug or self.URL[url]['prod'] == 'test':
                    return
                self.alert(url, "ATTEMPTING PURCHASE")
            WebDriverWait(self.driver, 30).until(
                ec.element_to_be_clickable((By.XPATH, xpath))
            )
            el.click()

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
                            self.driver.save_screenshot(f"scrn/PurchaseComplete-{self.domain}-{self.URL[url]['prod']}-{datetime.now().strftime('%a-%b-%d-%H-%M-%S')}.png")
                            return True
                    if pagei < len(self.site.layout) and self.site.page[
                        self.site.layout[pagei]] not in self.driver.current_url:
                        self.driver.get(self.site.url(pagei))
                    sleep(2)
                    pagei += 1
            # we are not on a recognized page
            self.driver.save_screenshot("scrn/error/{}.png".format(self.driver.current_url))
            return False
