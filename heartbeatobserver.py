#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# to format the code, run `black -tpy38 -l80 heartbeatobserver.py`.
# to update requirements list, run `pip freeze > requirements.txt`.
# to install requirements, run `pip install -r requirements.txt`.

from datetime import datetime
import os
import re
import sys
import time
from typing import Callable

import dotenv
import requests
import yaml


def parseInt(value: str) -> int:
    if value == "":
        return 0
    if re.search(r"^-?\d+$", value):
        return int(value)
    if re.search(r"^\+", value):
        raise Exception(
            "Remove the plus mark at the head of the value: " + value
        )
    raise Exception("The given value is not an integral string: " + value)


class HeartBeatObserver:
    HEALTHS = []

    def __init__(_):
        _.APP_ROOT = os.path.dirname(os.path.realpath(__file__))
        _.getConfig()

    def _getListFromEnv(noUse, key):
        return [t for t in os.getenv(key, default="").split(",") if len(t) > 0]

    def _getIntegerFromEnv(noUse, key):
        v = parseInt(os.getenv(key, default="0"))
        return v if v > 0 else 1

    def getConfig(_):
        # get from env or dotenv
        dotenv.load_dotenv()
        _.WEBHOOK_URL = os.getenv("WEBHOOK_URL", default="")
        _.OBSERVATION_TARGETS = _._getListFromEnv("OBSERVATION_TARGETS")
        _.USER_IDS_FOR_PINGING = _._getListFromEnv("USER_IDS_FOR_PINGING")
        _.NUMBER_OF_ATTEMPTS = _._getIntegerFromEnv("NUMBER_OF_ATTEMPTS")
        _.ATTEMPT_INTERVAL = _._getIntegerFromEnv("ATTEMPT_INTERVAL")

        try:
            # overwrite them with data from yaml
            s = open(f"{_.APP_ROOT}/config.yaml", "r")
            c = yaml.safe_load(s)

            names = [
                "webhook_url",
                "observation_targets",
                "user_ids_for_pinging",
                "number_of_attempts",
                "attempt_interval",
            ]
            for n in names:
                try:
                    setattr(_, n.upper(), c[n])
                except KeyError:
                    pass
        except FileNotFoundError:
            pass

        if _.WEBHOOK_URL == "":
            raise Exception("WEBHOOK_URL is not set")

    def checkTargetHealths(_):
        for target in _.OBSERVATION_TARGETS:
            health = _.HealthCheck(target)
            for noUse in range(_.NUMBER_OF_ATTEMPTS):
                _.checkTargetHealth(health)

                if health.RETRY:
                    time.sleep(_.ATTEMPT_INTERVAL)
                else:
                    break
            _.HEALTHS.append(health)

    def checkTargetHealth(_, health):
        try:
            health.appendResult(requests.get(health.TARGET))
        except requests.ConnectionError:
            health.appendError("Failed to connect")
        except requests.Timeout:
            health.appendError("Timeout", retry=True)
        except requests.TooManyRedirects:
            health.appendError("Too many redirects occurred")
        except requests.HTTPError:
            health.appendError("HTTP error occurred")
        except:
            health.appendError("Unknown error")

    def formatPingedUsers(_, userIds):
        return " ".join([f"<@{v}>" for v in userIds])

    def run(_):
        _.checkTargetHealths()

        def isPinging():
            return any([not h.isGood() for h in _.HEALTHS])

        def note(health):
            return (
                f" (interval between each attempt was {_.ATTEMPT_INTERVAL} {'second' if _.ATTEMPT_INTERVAL == 1 else 'seconds'})"
                if len(health.STATUSES) > 1
                else ""
            )

        content = "\n".join(
            [
                (
                    _.formatPingedUsers(_.USER_IDS_FOR_PINGING)
                    if isPinging()
                    else ""
                ),
                "> " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "\n".join(
                    [
                        health.TARGET
                        + " "
                        + (
                            ", ".join([str(s.CODE) for s in health.STATUSES])
                            if health.isGood()
                            else "__"
                            + ", ".join(
                                [s.getMessage() for s in health.STATUSES]
                            )
                            + "__"
                            + note(health)
                        )
                        for health in _.HEALTHS
                    ]
                ),
            ]
        )

        dataJson = {"content": content}
        requests.post(_.WEBHOOK_URL, data=dataJson)

    class HealthCheck:
        def __init__(_, target="", statuses=[]):
            _.TARGET = target
            _.STATUSES = [] + statuses  # to allocate new memory address
            _.RETRY = True

        def appendResult(_, result):
            _.RESULT = result
            _.STATUSES.append(_.Status(result.status_code))
            _.RETRY = not _.isGood()

        def appendError(_, error, retry=False):
            _.STATUSES.append(_.Status(message=error))
            _.RETRY = retry

        def isGood(_):
            return any([status.OK for status in _.STATUSES])

        class Status:
            def __init__(_, statusCode=0, message=""):
                _.CODE = statusCode
                _.OK = statusCode >= 200 and statusCode < 400
                _.addMessage(message)

            def addMessage(_, message):
                _.MESSAGE = message

            def getMessage(_):
                return _.MESSAGE if _.CODE == 0 else str(_.CODE)


def main():
    h = HeartBeatObserver()
    h.run()


if __name__ == "__main__":
    main()
else:
    print("Do not run me as a module")
    sys.exit(1)
