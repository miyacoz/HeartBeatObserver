#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime
import math
import os
import sys

import dotenv
import requests

def getWebhookUrl():
  webhookUrl = os.getenv("WEBHOOK_URL")
  if webhookUrl is None:
    print("WEBHOOK_URL is not set")
    sys.exit(1)
  return webhookUrl

def getObservationTargets():
  observationTargets = os.getenv("OBSERVATION_TARGETS").split(",")
  if len(observationTargets) == 0:
    print("OBSERVATION_TARGETS are not set")
    sys.exit(1)
  return observationTargets

def checkAvailabilitiesOfTargets():
  targets = getObservationTargets()
  return [(target, requests.get(target).status_code) for target in targets]

def getPingedUsers():
  pingedUserIds = os.getenv("USER_IDS_FOR_PINGING").split(",")
  userIdentifiers = ["<@" + userId + ">" for userId in pingedUserIds]
  return (" ".join(userIdentifiers) if len(pingedUserIds) > 0 else "<@here>") + " "

def isOkayStatus(statusCode):
  return statusCode >= 200 and statusCode < 400

def getMessage():
  # make this more testable
  users = getPingedUsers()
  loadAverages = [str(math.floor(la * 100) / 100) for la in os.getloadavg()]
  result = checkAvailabilitiesOfTargets()
  return "\n".join([
    (users if len([record[1] for record in result if not isOkayStatus(record[1])]) > 0 else ""),
    "> " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "Current loads: " + ", ".join(["`" + la + "`" for la in loadAverages]),
    "Availability checks:",
    "\n".join([record[0] + " " + (str(record[1]) if isOkayStatus(record[1]) else "__" + str(record[1]) + "__") for record in result]),
  ])

def main():
  dotenv.load_dotenv()

  dataJson = {
    "content": getMessage()
  }
  r = requests.post(getWebhookUrl(), data = dataJson)

if __name__ == "__main__":
  main()
else:
  print("Do not run me as a module")
