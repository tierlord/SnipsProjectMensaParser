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

def action_wrapper(hermes, intentMessage, conf):
    file = open("/home/pi/gerichte.txt")
    tag = intentMessage.slots.tag.first().value

    buffer = file.readlines()
    file.close()

    heute = buffer[:buffer.find("$Morgen")]
    morgen = buffer[buffer.find("$Morgen")+7:buffer.find("%Übermorgen")]
    umorgen = buffer[buffer.find("%Übermorgen")+11:]

    if tag == "heute":
        gerichte = heute
    if tag == "morgen":
        gerichte = morgen
    if tag == "übermorgen":
        gerichte = umorgen

    hermes.publish_end_session(current_session_id, text=gerichte)

if __name__ == "__main__":
    mqtt_opts = MqttOptions()
    with Hermes(mqtt_options=mqtt_opts) as h:
        h.subscribe_intent("{{intent_id}}", subscribe_intent_callback) \
         .start()