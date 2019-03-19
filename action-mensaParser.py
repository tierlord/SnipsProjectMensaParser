#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import configparser
from hermes_python.hermes import Hermes
from hermes_python.ffi.utils import MqttOptions
from hermes_python.ontology import *
import io

CONFIGURATION_ENCODING_FORMAT = "utf-8"
CONFIG_INI = "config.ini"

class SnipsConfigParser(configparser.SafeConfigParser):
    def to_dict(self):
        return {section : {option_name : option for option_name, option in self.items(section)} for section in self.sections()}


def read_configuration_file(configuration_file):
    try:
        with io.open(configuration_file, encoding=CONFIGURATION_ENCODING_FORMAT) as f:
            conf_parser = SnipsConfigParser()
            conf_parser.readfp(f)
            return conf_parser.to_dict()
    except (IOError, configparser.Error) as e:
        return dict()

def subscribe_intent_callback(hermes, intentMessage):
    conf = read_configuration_file(CONFIG_INI)
    action_wrapper(hermes, intentMessage, conf)

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

    global gerichte
    gerichte += gericht + ".\n"

def getMeals():
    global gerichte
    meals = driver.find_elements_by_class_name("meal__content")
    for meal in meals:
        title = meal.find_element_by_class_name("meal__content__title").text
        if(title == "Tagesmenü"):
            gerichte += "Als Tagesgericht gibt es "
            parseMeal(meal)
        if(title == "Tagesmenü vegetarisch"):
            gerichte += "Das vegetarische Tagesgericht ist "
            parseMeal(meal)
        if(title == "Angebot des Tages"):
            gerichte += "Angebot des Tages ist "
            parseMeal(meal)
        if(title == "Salat-/ Gemüsebuffet 100g"):
            gerichte += "Beim Buffet findest du "
            parseMeal(meal, True)

def clickLink(link, trys=0):
    if trys > 5:
        print("Error")
        return
    link.click()
        
def chooseDay(request):
    date = datetime.datetime.now()

    if request != "heute":
        if request != "morgen" and request != "übermorgen":
            print("Not supported")
        else:
            nxt = driver.find_element_by_class_name("meal-calendar__next-btn")
            if request == "morgen":
                date = date + datetime.timedelta(days=1)
                nxt.click()
            if request == "übermorgen":
                date = date + datetime.timedelta(days=2)
                nxt.click()
                time.sleep(1)
                nxt.click()

            dateStr = str('{:02d}'.format(date.day)) + "." + str('{:02d}'.format(date.month)) + "."
            print ("Requesting date: " + dateStr)

    global gerichte
    gerichte += "Folgende Gerichte gibt es " + request + " in der Mensa:\n"
    getMeals()
    driver.close()
    return gerichte

gerichte = ""
driver = None

def action_wrapper(hermes, intentMessage, conf):
    import datetime, time
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    browseroptions = Options()
    browseroptions.headless = True

    global driver
    driver = webdriver.chrome(options=browseroptions, executable_path=r'/home/pi/chromedriver')
    driver.get("https://www.my-stuwe.de/mensa/mensa-reutlingen/")

    gerichte = chooseDay(intentMessage.slots.tag.first().value)

    if gerichte is None:
        gerichte = "Es gab wohl einen Fehler."

    current_session_id = intentMessage.session_id
    hermes.publish_end_session(current_session_id, text=gerichte)

if __name__ == "__main__":
    mqtt_opts = MqttOptions()
    with Hermes(mqtt_options=mqtt_opts) as h:
        h.subscribe_intent("{{intent_id}}", subscribe_intent_callback) \
         .start()