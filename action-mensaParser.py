#!/usr/bin/env python3

from hermes_python.hermes import Hermes
from hermes_python.ontology.dialogue.session import DialogueConfiguration
import paho.mqtt.client as mqtt
import json, time
from threading import Thread

meals_json = None
gericht_gewaehlt = None
client = None

def parse_meals(meals, day, menu):
    msg = ""
    for d in meals['meals']:
        if not day or d['day'] == day:
            for meal in d['menu']:
                if not menu or meal['title'] == menu:
                    mealstring = meal['title'] + ":\n" + meal['content']
                    print(mealstring)
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
            if day and menu:
                meals_string += " möchtest du das bestellen?"
                global gericht_gewaehlt
                gericht_gewaehlt = menu
                dialogue_conf = DialogueConfiguration() \
                .enable_intent("tierlord:Bestaetigen")
                return hermes.publish_continue_session(message.session_id, meals_string, ["tierlord:Bestaetigen"])
            meals_string += " was möchtest du bestellen?"
            return hermes.publish_continue_session(message.session_id, meals_string, ["tierlord:Waehlen"])
        time.sleep(1)
    return hermes.publish_end_session(message.session_id, "Es konnten keine Gerichte geladen werden.")

def gerichteVorlesen (hermes, message):
    global client
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect("192.168.0.227", 1883, 60)
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
    msg = "Okay, ich habe " + request + " für dich bestellt."
    global client
    client.publish("menu/bestellung", request, retain=True)
    return hermes.publish_end_session(message.session_id, msg)

def gerichtBestaetigen (hermes, message):
    msg = "Alles klar. Ich habe " + gericht_gewaehlt + " für dich bestellt."
    global client
    client.publish("menu/bestellung", gericht_gewaehlt, retain=True)
    dialogue_conf = DialogueConfiguration() \
    .disable_intent("tierlord:Bestaetigen") \
    return hermes.publish_end_session(message.session_id, msg)


with Hermes("localhost:1883") as h:
    h \
        .subscribe_intent("tierlord:WasGibts", gerichteVorlesen) \
        .subscribe_intent("tierlord:Waehlen", gerichtWaehlen) \
        .subscribe_intent("tierlord:Bestaetigen", gerichtBestaetigen) \
        .start()