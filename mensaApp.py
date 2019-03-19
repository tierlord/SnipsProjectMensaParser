from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.options import Options
import datetime, time

options = Options()
options.add_argument("--headless")

driver = webdriver.Firefox(options=options)

driver.get("https://www.my-stuwe.de/mensa/mensa-reutlingen/")

gerichte = ""

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