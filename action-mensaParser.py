#!/usr/bin/env python3

from hermes_python.hermes import Hermes

path = "/var/tmp/gerichte.txt"
#path = "gerichte.txt"

def gerichteVorlesen (hermes, message):
    print("Gerichte Vorlesen..")
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

    request = message.slots.tag.first().value
    
    msg = "Folgende Gerichte gibt es " + request + ":\n"

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
    
    return hermes.publish_continue_session(message.session_id, msg, ["tierlord:Waehlen"])


def gerichtWaehlen (hermes, message):
    request = message.slots.gericht.first().value
    if request == "Angebot":
        request = "das Angebot des Tages"
    msg = "Okay, ich habe " + request + " für dich bestellt."
    return hermes.publish_end_session(message.session_id, msg)


with Hermes("localhost:1883") as h:
    h \
        .subscribe_intent("tierlord:WasGibts", gerichteVorlesen) \
        .subscribe_intent("tierlord:Waehlen", gerichtWaehlen) \
        .start()