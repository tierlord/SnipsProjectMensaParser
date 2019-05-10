#!/usr/bin/env python3

from hermes_python.hermes import Hermes
import paho.mqtt.client as mqtt
import json, time
from threading import Thread

MQTT_ADDR = "localhost"

meals_json = None
gericht_gewaehlt = None

def parse_meals(meals, day, menu_request):
    msg = ""
    if menu_request:
        print("MENU REQUEST: " + menu_request)
        menu = menu_request
        if "vegetarisch" in menu:
            menu = "Tagesmenü vegetarisch"
        if "hauptmenü" in menu:
            menu = "Tagesmenü"
        if "angebot" in menu:
            menu = "Angebot des Tages"
        global gericht_gewaehlt
        gericht_gewaehlt = menu
    for d in meals['meals']:
        if not day or d['day'] == day:
            for meal in d['menu']:
                if not menu or meal['title'] == menu:
                    mealstring = meal['title'] + ":\n" + meal['content']
                    msg += mealstring + ".\n"
    return msg

def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    client.subscribe("menu/#")

def on_message(client, userdata, msg):
    meals = json.loads(msg.payload.decode("utf-8-sig"))
    client.disconnect()
    global meals_json
    meals_json = meals

def receive_meals(hermes, message, day, menu):
    for i in range (5):
        if meals_json:
            meals_string = parse_meals(meals_json, day, menu)
            if meals_string == "":
                msg = "Für " + day + " konnte kein Gericht gefunden werden."
                return hermes.publish_end_session(message.session_id, msg)
            if day and menu:
                msg = day + " gibt es:\n"
                print("MEALS_STRING: " + meals_string)
                msg += meals_string + " möchtest du das bestellen?"
                return hermes.publish_continue_session(message.session_id, msg, ["tierlord:Bestaetigen"])
            return hermes.publish_end_session(message.session_id, meals_string)
        time.sleep(1)
    return hermes.publish_end_session(message.session_id, "Es konnten keine Gerichte geladen werden.")

def gerichteVorlesen (hermes, message):
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_ADDR, 1883, 60)
    client.loop_forever()
    tag = None
    menu = None

    if message.slots.tag:
        tag = message.slots.tag.first().value

    if message.slots.menu:
        menu = message.slots.menu.first().value

    t = Thread(target=receive_meals, args=(hermes,message,tag,menu))
    t.start()
    t.join()


def gerichtWaehlen (hermes, message):
    request = message.slots.gericht.first().value
    if request == "Angebot":
        request = "das Angebot des Tages"
    if "vegetarisch" in request:
        request = "Tagesmenü vegetarisch"
    client = mqtt.Client()
    client.connect(MQTT_ADDR, 1883, 60)
    client.publish("menu/bestellung", request, retain=True)
    msg = "Okay, ich habe " + request + " für dich bestellt."
    return hermes.publish_end_session(message.session_id, msg)

def gerichtBestaetigen (hermes, message):
    if message.slots.jaNein:
        if message.slots.jaNein.first().value == "nein":
            hermes.publish_end_session(message.session_id, "Okay. Bestellung abgebrochen.")
            return
    global gericht_gewaehlt
    if not gericht_gewaehlt:
        hermes.publish_end_session(message.session_id, "Etwas ist schief gegangen.")
        return
    msg = "Alles klar. Ich habe " + gericht_gewaehlt + " für dich bestellt."
    client = mqtt.Client()
    client.connect(MQTT_ADDR, 1883, 60)
    print("Publish bestellung")
    client.publish("menu/bestellung", gericht_gewaehlt, retain=True)
    gericht_gewaehlt = None
    hermes.publish_end_session(message.session_id, msg)

def session_ended(hermes, session_ended_message):
    global meals_json
    meals_json = None

with Hermes("localhost:1883") as h:
    h \
        .subscribe_intent("tierlord:WasGibts", gerichteVorlesen) \
        .subscribe_intent("tierlord:Waehlen", gerichtWaehlen) \
        .subscribe_intent("tierlord:Bestaetigen", gerichtBestaetigen) \
        .subscribe_session_ended(session_ended) \
        .start()