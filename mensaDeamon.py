# -*- coding: utf-8 -*-

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
import datetime, time, json, traceback
import uuid # for the unique id
import paho.mqtt.client as mqtt

chrome_options = Options()
chrome_options.add_argument("--headless")

def createID():
    return str(uuid.uuid4())

def connect():
    try:
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except:
        print("Could not create driver. Trying again in 10 seconds.")
        traceback.print_exc()
        time.sleep(10)
        if not KeyboardInterrupt:
            connect()

def fetchSite(driver):
    driver.get("https://www.my-stuwe.de/mensa/mensa-reutlingen/")

def removeIngrHint(gericht):
    klammer_auf = gericht.find('[')
    klammer_zu = gericht.find(']') + 1
    if klammer_auf != -1:
        return gericht[:klammer_auf] + gericht[klammer_zu:]
    return gericht

def parseMeal(meal, salat=False):
    content = meal.find_element_by_class_name("meal__content__menu").find_elements_by_class_name("meal__content__menu__item")
    gericht = ""
    nr_items = len(content)
    if salat:
        gericht += "Salat und Gemüse"
        for i in range (1, nr_items):
            gericht += ", "
            gericht += removeIngrHint(content[i].text)
    else:
        for i in range (0, nr_items):
            gericht += removeIngrHint(content[i].text)
            if i == nr_items-2:
                gericht += " und "
            if i < nr_items-2:
                if i == 0:
                    gericht += " mit "
                else:
                    gericht += ", "

    gericht = gericht.replace("  ", " ") #
    gericht = gericht.replace(" ,", ",") # stripping
    gericht = gericht.replace(" .", ".") #
    gericht = gericht.replace("mit mit", "mit")
    return gericht

def getMeals():
    gerichte = []

    meals = driver.find_elements_by_class_name("meal__content")
    for meal in meals:
        title = meal.find_element_by_class_name("meal__content__title").text
        gericht = {
            "title": title,
        }
        content = parseMeal(meal)
        if "Tages" in title and content != "":
            gericht["content"] = content
            gericht["id"] = createID()
            gerichte.append(gericht)
    return gerichte

def chooseDay():
    date = datetime.datetime.now()

    menu_heute = {}
    menu_morgen = {}
    menu_umorgen = {}

    menu_heute["day"] = "heute"
    menu_morgen["day"] = "morgen"
    menu_umorgen["day"] = "übermorgen"

    menu_heute["menu"] = getMeals()
    driver.execute_script('document.getElementsByClassName("meal-calendar__next-btn")[0].click();')
    time.sleep(1)
    menu_morgen["menu"] = getMeals()
    driver.execute_script('document.getElementsByClassName("meal-calendar__next-btn")[0].click();')
    time.sleep(1)
    menu_umorgen["menu"] = getMeals()

    dateStr = "%02d.%02d.%4d" % (date.day, date.month, date.year)

    gerichte = [menu_heute, menu_morgen, menu_umorgen]

    jsonObj = {
        "updated": dateStr,
        "meals": gerichte
    }

    return json.dumps(jsonObj, indent=4, ensure_ascii=False)

def sendMQTT (jsonString):
    HOST = 'localhost'
    PORT = 1883
    client = mqtt.Client()
    client.connect(HOST, PORT, 60)
    client.publish(topic="menu/mensa", payload=jsonString, retain=True, qos=1)

while True:
    driver = connect()
    fetchSite(driver)
    gerichte = chooseDay()
    print(gerichte)
    sendMQTT(gerichte)
    time.sleep(3600)
    if KeyboardInterrupt:
        break