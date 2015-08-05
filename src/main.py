#!/usr/bin/env python


from __future__ import print_function
import os
import sys
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)

# core
from   datetime import datetime, timedelta
from   functools import wraps
import logging
import pprint
import random
import re
import sys
import time

# pypi
import argh
from clint.textui import progress
import funcy
from splinter import Browser
from selenium.common.exceptions import TimeoutException, UnexpectedAlertPresentException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import selenium.webdriver.support.expected_conditions as EC
import selenium.webdriver.support.ui as ui

# local
import conf  # it is used. Even though flymake cant figure that out.


logging.basicConfig(
    format='%(lineno)s %(message)s',
    level=logging.WARN
)

random.seed()

pp = pprint.PrettyPrinter(indent=4)

base_url = 'http://www.freelotto.com/'

action_path = dict(
    login="login.asp",
    viewads='viewAds.asp',
    dashboard='Dot_MembersPage.asp',
    withdraw='DotwithdrawForm.asp'
)

one_minute = 60
three_minutes = 3 * one_minute
ten_minutes = 10 * one_minute
one_hour = 3600


def url_for_action(action):
    return "{0}/{1}".format(base_url, action_path[action])


def loop_forever():
    while True: pass


def clear_input_box(box):
    box.type(Keys.CONTROL + "e")
    for i in xrange(100):
        box.type(Keys.BACKSPACE)
    return box


def page_source(browser):
    document_root = browser.driver.page_source
    return document_root


def wait_visible(driver, locator, by=By.XPATH, timeout=30):
    try:
        return ui.WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((by, locator)))
    except TimeoutException:
        raise Exception("Element not found by {0} using {1}".format(
            by, locator))


def trap_unexpected_alert(func):
    @wraps(func)
    def wrapper(self):
        try:
            return func(self)
        except UnexpectedAlertPresentException:
            print("Caught unexpected alert.")
            return 254
        except WebDriverException:
            print("Caught webdriver exception.")
            return 254

    return wrapper


def trap_any(func):
    @wraps(func)
    def wrapper(self):
        try:
            return func(self)
        except:
            print("Caught exception.")
            return 254

    return wrapper


def trap_alert(func):
    @wraps(func)
    def wrapper(self):
        try:
            return func(self)
        except UnexpectedAlertPresentException:
            print("Caught UnexpectedAlertPresentException.")
            return 254
        except WebDriverException:
            print("Caught webdriver exception.")
            return 253

    return wrapper


def get_element_html(driver, elem):
    return driver.execute_script("return arguments[0].innerHTML;", elem)


class Entry(object):

    def __init__(
            self, loginas, browser, action, surf
    ):

        modobj = sys.modules['conf']
        print(modobj)
        d = getattr(modobj, loginas)

        self._username = d['username']
        self._password = d['password']
        self.browser = browser
        self.action = action
        self.surf = surf

    def login(self):
        print("Logging in...")

        self.browser_visit('login')

        self.browser.find_by_name('email').type(self._username)
        self.browser.find_by_name('password').type(self._password)
        self.browser.find_by_id('btn-login').click()

    def play(self):
        self.browser.find_by_name('quick').click()
        elem = wait_visible(self.browser.driver, 'submit-red', by=By.ID)
        elem.click()

        wait_visible(
            self.browser.driver, 'btn-advert-click2win', by=By.ID).click()



    def browser_visit(self, action_label):
        try:
            logging.debug("Visiting URL for {0}".format(action_label))
            self.browser.visit(url_for_action(action_label))
            return 0
        except UnexpectedAlertPresentException:
            print("Caught UnexpectedAlertPresentException.")
            logging.warn("Attempting to dismiss alert")
            alert = self.driver.switch_to_alert()
            alert.dismiss()
            return 254
        except WebDriverException:
            print("Caught webdriver exception.")
            return 253

    def view_ads(self, buy_pack=False):
        for i in xrange(1, self.surf+1):
            while True:
                print("Viewing ad {0}".format(i))
                result = self.view_ad()
                if result == 0:
                    break

        self.calc_account_balance()
        self.calc_time(stay=False)
        if buy_pack:
            self.buy_pack()

    @trap_alert
    def view_ad(self):

        logging.warn("Visiting viewads")
        self.browser_visit('viewads')
        time.sleep(random.randrange(2, 5))

        logging.warn("Finding text_button")
        buttons = self.browser.find_by_css('.text_button')

        logging.warn("Clicking button")
        buttons[0].click()

        logging.warn("Solving captcha")
        self.solve_captcha()

        logging.warn("wait_on_ad2")
        self.wait_on_ad2()

        return 0

    def wait_on_ad(self):
        time_to_wait_on_ad = random.randrange(40, 50)
        for i in progress.bar(range(time_to_wait_on_ad)):
            time.sleep(1)

    def wait_on_ad2(self):
        wait_visible(self.browser.driver,
                     '//img[@src="images/moreadstop.gif"]',
                     By.XPATH,
                     60)

    def time_macro(self):
        self.calc_account_balance()
        self.calc_time()

    def buy_pack(self):
        self.calc_account_balance()
        print("Balance: {}".format(self.account_balance))
        if self.account_balance >= 49.99:
            self._buy_pack()

    def withdraw(self):
        self.calc_account_balance()
        self.browser_visit('withdraw')
        select = ui.Select(
            wait_visible(self.browser.driver, "withdrawPmt", By.ID)
        )
        select.select_by_visible_text("Solid Trust Pay")
        i = self.browser.find_by_name('withdrawAmt')
        clear_input_box(i).type(str(self.account_balance))
        self.browser.find_by_name('transPin').type(self._pin)
        wait_visible(self.browser.driver, 'Submit4', by=By.NAME).click()
        wait_visible(self.browser.driver, 'Submit465', by=By.NAME).click()


    def _buy_pack(self):
        a = self.browser.find_by_xpath(
            '//a[@href="Dot_CreditPack.asp"]'
        )
        print("A: {0}".format(a))
        a.click()

        button = wait_visible(self.browser.driver, 'Preview', by=By.NAME)
        button.click()

        button = wait_visible(self.browser.driver, 'Preview', by=By.NAME)
        button.click()

    def calc_account_balance(self):

        time.sleep(1)

        logging.warn("visiting dashboard")
        self.browser_visit('dashboard')

        logging.warn("finding element by xpath")
        elem = self.browser.find_by_xpath(
            '/html/body/table[2]/tbody/tr/td[2]/table/tbody/tr/td[2]/table[6]/tbody/tr/td/table/tbody/tr[2]/td/h2[2]/font/font'
        )

        print("Elem Text: {}".format(elem.text))

        self.account_balance = float(elem.text[1:])

        print("Available Account Balance: {}".format(self.account_balance))

    def calc_credit_packs(self):

        time.sleep(1)

        logging.warn("visiting dashboard")
        self.browser_visit('dashboard')

        logging.warn("finding element by xpath")
        elem = self.browser.find_by_xpath(
            "//font[@color='#009900']"
        )

        print("Active credit packs = {0}".format(elem[0].text))
        # for i, e in enumerate(elem):
        #     print("{0}, {1}".format(i, e.text))

    def calc_clicked(self):

        time.sleep(1)

        self.browser_visit('dashboard')

        #logging.warn("finding element by xpath")
        elem = self.browser.find_by_xpath(
            '/html/body/table[2]/tbody/tr/td[2]/table/tbody/tr/td[2]/table[2]/tbody/tr/td'
        )

        # The click status box says: <div align="center"><strong><font color="#FFFFFF">Surf Clicked Today: 0<br>You have clicked on 10 ads within the last 24 hours<br>
        # The click status box says: <div align="center"><strong><font color="#FFFFFF">Surf Clicked Today: 6<br>You have NOT clicked on 10 ads within the last 24 hours<br>

        html = get_element_html(self.browser.driver, elem[0]._element)
        find = html.find("You have NOT clicked on")

        print("HTML={0}. Find={1}.".format(html, find))

        if html.find("You have NOT clicked on") != -1:
            return -1
        else:
            clicked = funcy.silent(int)(
                funcy.re_find(r'You have clicked on (\d+)', html))
            return clicked

        raise("Could not calculate clicked.")

    def calc_time(self, stay=True):

        time.sleep(3)

        self.browser_visit('dashboard')

        elem = self.browser.find_by_xpath(
            '//table[@width="80%"]/tbody/tr/td[1]'
        )

        remaining = elem.text.split()
        for i, v in enumerate(remaining):
            print(i, v)

        indices = dict(
            hours=17,
            minutes=19
        )

        hours = int(remaining[indices['hours']])
        minutes = int(remaining[indices['minutes']])

        next_time = datetime.now() + timedelta(
            hours=hours, minutes=minutes)

        print("Next time to click is {0}".format(
            next_time.strftime("%Y-%m-%d %H:%M")))

        if stay:
            loop_forever()

    def solve_captcha(self):
        time.sleep(3)

        t = page_source(self.browser).encode('utf-8').strip()
        #print("Page source {0}".format(t))

        captcha = funcy.re_find(
            """ctx.strokeText\('(\d+)'""", t)

        #print("CAPTCHA = {0}".format(captcha))

        self.browser.find_by_name('codeSb').fill(captcha)

        time.sleep(6)
        button = self.browser.find_by_name('Submit')
        button.click()

def main(loginas, random_delay=False, action='click', stayup=False, surf=10):

    if random_delay:
        random_delay = random.randint(1, 15)
        print("Random delay = {0}".format(random_delay))
        time.sleep(one_minute * random_delay)

    with Browser() as browser:

        browser.driver.set_window_size(1200, 1100)

        e = Entry(loginas, browser, action, surf)

        e.login()
        e.play()
        loop_forever()




def conda_main():
    argh.dispatch_command(main)

if __name__ == '__main__':
    argh.dispatch_command(main)
