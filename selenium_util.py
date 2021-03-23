from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.remote.remote_connection import LOGGER as selenium_logger

def button_click_using_xpath(d, xpath):
    button = WebDriverWait(d, 10).until(
        ec.element_to_be_clickable((By.XPATH, xpath))
    )
    button.click()

def wait_for_page(d, title, time=30):
    WebDriverWait(d, time).until(ec.title_is(title))

def wait_for_element_by_xpath(d, e_path, time=30):
    return WebDriverWait(d, time).until(
        ec.presence_of_element_located((By.XPATH, e_path))
    )

def wait_for_element(d, e_id, time=30):
    return WebDriverWait(d, time).until(ec.presence_of_element_located((By.ID, e_id)))

def field_send_keys(d, xpath, keys):
    elem = d.find_element_by_xpath(xpath)
    elem.clear()
    elem.send_keys(keys)