#!/usr/bin/env python3

from hermes_python.hermes import Hermes
import paho.mqtt.client as mqtt
import json, time
from threading import Thread

######################################################################
# Hier wird die Adresse des MQTT Brokers eingestellt
# Snips bietet seinen eigenen Broker, sodass localhost hier genuegt
MQTT_ADDR = "localhost"
# Der Hostname des Raspberry Pi sollte in einer Datei namens "hostname"
# an diesem Pfad abgelegt werden
# Dieser Hostname wird zur Identifikation der Essensbestellung genutzt
hostnamePath = "/var/tmp/hostname"
######################################################################

meals_json = None
gericht_gewaehlt = None

f = open(hostnamePath, "r")
hostname = f.readline()
f.close()

# sucht in dem JSON (meals) nach angeforderten Menue (menu_request)
# fuer den angeforderten Tag (day) und gibt einen String zurueck
def parse_meals(meals, day, menu_request):
    msg = ""
    menu = menu_request
    if menu_request:
        menu = menu_request
        if "vegetarisch" in menu or "vegan" in menu:
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
    client.subscribe("menu/mensa")

def on_message(client, userdata, msg):
    meals = json.loads(msg.payload.decode("utf-8-sig"))
    client.disconnect()
    global meals_json
    meals_json = meals

# Sendet die empfangenen Gerichte an das TTS
# Bei Fehlern wird eine Fehlermeldung an das TTS gesendet
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
    return hermes.publish_end_session(message.session_id, "Es konnten keine Gerichte geladen werden.")

# verbindet den MQTT client, extrahiert die slots aus dem intent
# und startet receive_meals als neuen thread
def gerichteVorlesen (hermes, message):
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_ADDR, 1883, 60)
    client.loop_forever(timeout=5)
    tag = None
    menu = None

    if message.slots.tag:
        tag = message.slots.tag.first().value

    if message.slots.menu:
        menu = message.slots.menu.first().value

    receive_meals(hermes, message, tag, menu)

def gerichtWaehlen (hermes, message):
    global hostname

    request = message.slots.gericht.first().value
    if request == "Angebot":
        request = "das Angebot des Tages"
    if "vegetarisch" in request:
        request = "Tagesmenü vegetarisch"
    client = mqtt.Client()
    client.connect(MQTT_ADDR, 1883, 60)

    bestellung_obj = {
        "von" : hostname,
        "gericht": request,
        "zeit" : time.ctime()
    }
    json_str = json.dumps(bestellung_obj, ensure_ascii=False)

    client.publish("menu/bestellung", payload=json_str, retain=True)
    msg = "Okay, ich habe " + request + " für dich bestellt."
    return hermes.publish_end_session(message.session_id, msg)

def gerichtBestaetigen (hermes, message):
    global hostname

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
    bestellung_obj = {
        "von" : hostname,
        "gericht": gericht_gewaehlt,
        "zeit" : time.ctime()
    }

    json_str = json.dumps(bestellung_obj, ensure_ascii=False)

    print("Publish bestellung")
    client.publish("menu/bestellung", payload=json_str, retain=True)
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