#!/usr/bin/env python3

from hermes_python.hermes import Hermes

path = "/var/tmp/gerichte.txt"
#path = "gerichte.txt"

def gerichteVorlesen (request):
    try:
        gerichteFile = open(path, "r")
        gerichte = gerichteFile.readlines()
        gerichteFile.close()
    except:
        print("gerichte.txt not found!")
        exit()

    indexHeute = 0
    indexMorgen = 0
    indexUmorgen = 0

    for i in range (len(gerichte)):
        line = gerichte[i]
        if("$Heute" in line):
            indexHeute = i
        if("$Morgen:" in line):
            indexMorgen = i
        if("$Übermorgen:" in line):
            indexUmorgen = i

    msg = "Folgende Gerichte habe ich gefunden:\n"

    if request == "heute":
        for i in range (indexHeute + 1, indexMorgen - 1):
            msg += gerichte[i] + "\n"
    if request == "morgen":
        for i in range (indexMorgen + 1, indexUmorgen - 1):
            msg += gerichte[i] + "\n"
    if request == "übermorgen":
        for i in range (indexUmorgen + 1, len(gerichte)):
            msg += gerichte[i] + "\n"
    msg = msg.replace("~", "")
    msg += "\nWas darf ich für dich bestellen?"
    return msg


def gerichtWaehlen (request):
    msg = "Okay, ich habe " + request + " für dich bestellt."
    return msg


def subscribe_intent_callback(hermes, intent_message):
    intentName = intent_message.intent.intent_name

    if "WasGibts" in intentName:
        request = intent_message.slots.tag.first().value
        hermes.publish_continue_session(intent_message.session_id, gerichteVorlesen(request), ["Waehlen"])

    if "Waehlen" in intentName:
        request = intent_message.slots.gericht.first().value
        hermes.publish_end_session(intent_message.session_id, gerichtWaehlen(request))


if __name__ == "__main__":
    with Hermes("localhost:1883") as h:
        h\
            .subscribe_intents(subscribe_intent_callback)\
            .start()