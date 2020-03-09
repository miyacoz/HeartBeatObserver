#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime
import math
import os
import re
import sys
import time
from typing import Callable

import dotenv
import psutil
import requests

def memoize(f: Callable) -> Callable:
  table = {}
  def func(*args):
    if not args in table: table[args] = f(*args)
    return table[args]
  return func

def parseInt(value: str) -> int:
  if value == '': return 0
  if re.search(r'^-?\d+$', value): return int(value)
  if re.search(r'^\+', value): raise Exception('Remove the plus mark at the head')
  raise Exception('The given value is not an integral string')

def getWebhookUrl():
  webhookUrl = os.getenv('WEBHOOK_URL', default = '')
  if webhookUrl == '': raise Exception('WEBHOOK_URL is not set')
  return webhookUrl

def getObservationTargets(): return [target for target in os.getenv('OBSERVATION_TARGETS', default = '').split(',') if len(target) > 0]

@memoize
def getRetryInterval():
  try:
    retryInterval = parseInt(os.getenv('ATTEMPT_INTERVAL', default = '1'))
    return retryInterval if retryInterval > 0 else 1
  except Exception as e: raise Exception('ATTEMPT_INTERVAL: ' + e)

def checkAvailabilitiesOfTargets():
  targets = getObservationTargets()
  numberOfAttempts = parseInt(os.getenv('NUMBER_OF_ATTEMPTS', default = '0'))
  tries = numberOfAttempts if numberOfAttempts > 0 else 1
  retryInterval = getRetryInterval()
  result = []
  for target in targets:
    statuses = []
    for _ in range(tries):
      try:
        statuses.append(str(requests.get(target).status_code))
        break
      except requests.exceptions.ConnectionError: statuses.append('Failed to connect')
      except requests.exceptions.Timeout: statuses.append('Timeout')
      except requests.exception.TooManyRedirects: statuses.append('Too many redirects occurred')
      except: statuses.append('Unknown error')
      time.sleep(retryInterval)
    result.append({'target': target, 'statuses': statuses})
  return result

def getPingedUsers():
  userIds = [userId for userId in os.getenv('USER_IDS_FOR_PINGING', default = '').split(',') if len(userId) > 0]
  if len(userIds) == 0: return ''
  userIdentifiers = ['<@' + userId + '>' for userId in userIds]
  return ' '.join(userIdentifiers) + ' '

def isOkayStatus(statusCode: str) -> bool:
  try:
    s = parseInt(statusCode)
    return s >= 200 and s < 400
  except: return False

def getMemoryUsage(data):
  def withUnit(n):
    if n > 1024 ** 3:
      g = n // (1024 ** 3)
      m = math.floor((n - (g * (1024 ** 3))) // (1024 ** 2) / 10)
      return str(g) + '.' + str(m) + ' G'
    if n > 1024 ** 2:
      m = n // (1024 ** 2)
      k = math.floor((n - (m * (1024 ** 2))) // (1024 ** 1) / 10)
      return str(m) + '.' + str(k) + ' M'
    if n > 1024 ** 1:
      m = n // (1024 ** 1)
      d = math.floor((n - (k * (1024 ** 1))) // (1024 ** 0) / 10)
      return str(k) + '.' + str(d) + ' K'
    return str(n)
  def isKeyAllowed(k):
    allowedKeys = ['total', 'available', 'percent', 'free']
    try:
      allowedKeys.index(k)
      return True
    except ValueError: return False
  return ', '.join(['`' + k + ': ' + withUnit(v) + '`' for k, v in data._asdict().items() if isKeyAllowed(k)])

def getMessage():
  # make this more testable
  users = getPingedUsers()
  loadAverages = [str(math.floor(la * 100) / 100) for la in os.getloadavg()]
  result = checkAvailabilitiesOfTargets()
  return '\n'.join([
    (users if len([record['statuses'] for record in result if not any([isOkayStatus(status) for status in record['statuses']])]) > 0 else ''),
    '> ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'Current loads: ' + ', '.join(['`' + la + '`' for la in loadAverages]),
    'Virtual memory usage: ' + getMemoryUsage(psutil.virtual_memory()),
    'Swap memory usage: ' + getMemoryUsage(psutil.swap_memory()),
    ('Availability checks:' if len(result) > 0 else ''),
    '\n'.join([
      record['target'] + ' ' + (
	', '.join(record['statuses'])
        if any([isOkayStatus(status) for status in record['statuses']])
        else '__' + ', '.join(record['statuses']) + '__' + (' (interval between each attempt was ' + str(getRetryInterval()) + ' second(s))' if len(record['statuses']) > 1 else '')
      ) for record in result
    ]),
  ])

def main():
  try:
    dotenv.load_dotenv()

    dataJson = {
      'content': getMessage()
    }
    requests.post(getWebhookUrl(), data = dataJson)
  except Exception as e:
    print(e)
    sys.exit(1)

if __name__ == '__main__': main()
else:
  print('Do not run me as a module')
  sys.exit(1)
