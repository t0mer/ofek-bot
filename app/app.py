import apprise
import yaml
import shutil
import os
import schedule
import time
import re
from os import path
from loguru import logger
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import InvalidSessionIdException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

SCHEDULES=os.getenv("SCHEDULES")

class Crawler:
    def __init__(self):
        self.kids = []
        self.delay = 5
        self.ofek_url = "https://myofek.cet.ac.il/he"
        self.user_field = '//*[@id="HIN_USERID"]'
        self.password_field = '//*[@id="Ecom_Password"]'
        self.edu_login_btn = '//*[@id="loginButton2"]'
        self.todo = ""
        self.tofix = ""
        self.wating = ""
        self.checked = ""
        self.apobj = apprise.Apprise()
        self.notifires = os.getenv("NOTIFIERS")
        self.config_path = 'config/config.yaml'
        self.get_kids()

    #### Setting ChromeOptions ####
    def init_browser(self):
        logger.info("Initializing browser")
        self.options = webdriver.ChromeOptions()
        self.options.add_argument("-incognito")
        self.options.add_argument("--headless")
        self.options.add_argument("disable-gpu")
        self.options.add_argument("--no-sandbox")
        self.options.add_argument('--start-maximized')
        self.options.add_argument("--disable-dev-shm-usage")
        self.browser = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=self.options)


    def init_notifires(self):
            if len(self.notifires)!=0:
                logger.debug("Setting Apprise notification channels")
                jobs=self.notifires.split()
                for job in jobs:
                    logger.debug("Adding: " + job)
                    self.apobj.add(job)


    def send_notification(self, title, message):
        if len(self.notifires)!=0:
            self.apobj.notify(
                body=message,
                title=title,
            )


    def get_kids(self):
        try:
            logger.info("Loading kids list")
            if not path.exists(self.config_path):
                shutil.copy('config.yaml', self.config_path)
            with open("config/config.yaml",'r',encoding='utf-8') as stream:
                try:
                    self.kids = yaml.safe_load(stream)
                except yaml.YAMLError as exc:
                    logger.error(exc)
        except Exception as e:
            logger.error(str(e))


    def crowl(self, username, password):
        logger.info("Crowling")
        try:

            # Open Ofek website
            self.browser.get(self.ofek_url)
            
            # Click the login button
            logger.debug("Click the login button")
            WebDriverWait(self.browser, self.delay).until(EC.presence_of_element_located(("xpath",'/html/body/div[2]/div/div/header/div[1]/div[1]/button'))).click()
            
            # Click edu.gov.il SSO button
            logger.debug("Click edu.gov.il SSO button")
            WebDriverWait(self.browser, self.delay).until(EC.presence_of_element_located(("xpath",'/html/body/div[2]/div/div/header/div[1]/div[1]/div/div/dialog/div/section/div/div/button/div'))).click()
          
            # Change to User/Pass auth type
            self.browser.get(self.browser.current_url.replace('EduCombinedAuthSms','EduCombinedAuthUidPwd'))

            # Enter Username
            WebDriverWait(self.browser, self.delay).until(EC.presence_of_element_located(("xpath", self.user_field))).send_keys(username)

            # Enter Password
            WebDriverWait(self.browser, self.delay).until(EC.presence_of_element_located(("xpath", self.password_field))).send_keys(password)

            # Click the login button
            self.browser.find_element("xpath",self.edu_login_btn).click()

            # Scrap tasks status
            logger.info("Scrapping...")
            self.todo = WebDriverWait(self.browser, self.delay).until(EC.presence_of_element_located(("xpath",'/html/body/div[2]/div/div/div[2]/main/div[3]/div[2]/div[1]/div[1]/div[1]/span'))).text
            self.tofix = WebDriverWait(self.browser, self.delay).until(EC.presence_of_element_located(("xpath",'/html/body/div[2]/div/div/div[2]/main/div[3]/div[2]/div[1]/div[2]/div/span'))).text
            self.checked = WebDriverWait(self.browser, self.delay).until(EC.presence_of_element_located(("xpath",'/html/body/div[2]/div/div/div[2]/main/div[3]/div[2]/div[1]/div[3]/div/span'))).text
            self.wating = WebDriverWait(self.browser, self.delay).until(EC.presence_of_element_located(("xpath",'/html/body/div[2]/div/div/div[2]/main/div[3]/div[2]/div[1]/div[4]/div/span'))).text
        except Exception as e:
            logger.error(e)


def main():
    try:

        for kid in crawler.kids['kids']:
            if not kid['username'] or not kid['password'] or not kid['name']:
                logger.warning("Kids list is empty or not configured")
                break
            logger.info("Getting tasks for: " + kid["name"])
            crawler.init_browser()
            crawler.crowl(str(kid['username']),str(kid['password']))
            title = "מצב משימות אופק של " + kid['name']
            message = crawler.todo + "\n" + crawler.tofix + "\n" + crawler.checked + "\n" + crawler.wating
            if has_tasks(crawler.todo,crawler.tofix):
                crawler.send_notification(title,message)
            else:
                logger.info("No tasks tbd for " + kid['name'])
            logger.debug("Closing browser")
            crawler.browser.quit()
    except Exception as e:
        logger.error(str(e))


def has_tasks(todo,tofix):
    todo_tasks = re.findall(r'\d+', todo)
    tofix_tasks = re.findall(r'\d+', tofix)
    return (int(todo_tasks[0]) > 0 or int(tofix_tasks[0]) > 0)

if __name__ == "__main__":
    try:
        crawler = Crawler()
        crawler.init_notifires()
        if not SCHEDULES:
            logger.debug("Setting default schedule to 16:00")
            schedule.every().day.at("16:00").do(main)
        else:
            for _schedule in SCHEDULES.split(','):
                logger.debug("Setting schedule to everyday at " + _schedule)
                schedule.every().day.at(_schedule).do(main)
        while True:
            schedule.run_pending()
            time.sleep(1)
    except Exception as e:
        logger.error(str(e))
