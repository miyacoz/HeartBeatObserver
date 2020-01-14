#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime
import math
import os
import sys

import dotenv
import psutil
import requests

def getWebhookUrl():
  webhookUrl = os.getenv("WEBHOOK_URL", default = "")
  if webhookUrl == "":
    print("WEBHOOK_URL is not set")
    sys.exit(1)
  return webhookUrl

def getObservationTargets():
  observationTargets = [target for target in os.getenv("OBSERVATION_TARGETS", default = "").split(",") if len(target) > 0]
  return observationTargets

def checkAvailabilitiesOfTargets():
  targets = getObservationTargets()
  result = []
  for target in targets:
    status = 0
    try:
      status = requests.get(target).status_code
    except requests.exceptions.ConnectionError:
      status = "Failed to connect"
    except requests.exceptions.Timeout:
      status = "Timeout"
    except requests.exception.TooManyRedirects:
      status = "Too many redirects occurred"
    result.append((target, status))
  return result

def getPingedUsers():
  userIds = [userId for userId in os.getenv("USER_IDS_FOR_PINGING", default = "").split(",") if len(userId) > 0]
  if len(userIds) == 0:
    return ""
  userIdentifiers = ["<@" + userId + ">" for userId in userIds]
  return " ".join(userIdentifiers) + " "

def isOkayStatus(statusCode):
  try:
    return statusCode >= 200 and statusCode < 400
  except:
    return False

def getMemoryUsage(data):
  def withUnit(n):
    if n > 1024 ** 3:
      g = n // (1024 ** 3)
      m = math.floor((n - (g * (1024 ** 3))) // (1024 ** 2) / 10)
      return str(g) + "." + str(m) + " G"
    if n > 1024 ** 2:
      m = n // (1024 ** 2)
      k = math.floor((n - (m * (1024 ** 2))) // (1024 ** 1) / 10)
      return str(m) + "." + str(k) + " M"
    if n > 1024 ** 1:
      m = n // (1024 ** 1)
      d = math.floor((n - (k * (1024 ** 1))) // (1024 ** 0) / 10)
      return str(k) + "." + str(d) + " K"
    return str(n)
  def isKeyAllowed(k):
    allowedKeys = ["total", "available", "percent", "free"]
    try:
      allowedKeys.index(k)
      return True
    except ValueError:
      return False
  return ", ".join(["`" + k + ": " + withUnit(v) + "`" for k, v in data._asdict().items() if isKeyAllowed(k)])

def getMessage():
  # make this more testable
  users = getPingedUsers()
  loadAverages = [str(math.floor(la * 100) / 100) for la in os.getloadavg()]
  result = checkAvailabilitiesOfTargets()
  return "\n".join([
    (users if len([record[1] for record in result if not isOkayStatus(record[1])]) > 0 else ""),
    "> " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "Current loads: " + ", ".join(["`" + la + "`" for la in loadAverages]),
    "Virtual memory usage: " + getMemoryUsage(psutil.virtual_memory()),
    "Swap memory usage: " + getMemoryUsage(psutil.swap_memory()),
    ("Availability checks:" if len(result) > 0 else ""),
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
