#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# to format the code, run `black -tpy38 -l80 heartbeatobserver.py`.
# to update requirements list, run `pip freeze > requirements.txt`.
# to install requirements, run `pip install -r requirements.txt`.

from datetime import datetime
import os
import re
import socket
import ssl
import sys
import time
from datetime import timedelta
from typing import Callable

import dotenv
import OpenSSL
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
        _.ALERT_SSL_EXPIRES_IN = _._getIntegerFromEnv("ALERT_SSL_EXPIRES_IN")

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
                "alert_ssl_expires_in",
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
                    if health.IS_SSL:
                        health.checkCertificate()
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
            return any([h.shouldAlert(_.ALERT_SSL_EXPIRES_IN) for h in _.HEALTHS])

        def note(health):
            return (
                f" (interval between each attempt was {_.ATTEMPT_INTERVAL} {'second' if _.ATTEMPT_INTERVAL == 1 else 'seconds'})"
                if len(health.STATUSES) > 1
                else ""
            )

        def showHealthyStatus(health):
            return (
                ", ".join([str(s.CODE) for s in health.STATUSES])
                + (f" (Expires: {health.getNotAfter()})")
                + (
                    (
                        f" *SSL Certificate expires in {health.getRemainingDays()} days!*"
                    )
                    if health.shouldAlert(_.ALERT_SSL_EXPIRES_IN)
                    else ""
                )
            )

        def showUnhealthyStatus(health):
            return (
                "__"
                + ", ".join([s.getMessage() for s in health.STATUSES])
                + "__"
                + note(health)
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
                            showHealthyStatus(health)
                            if health.isGood()
                            else showUnhealthyStatus(health)
                        )
                        for health in _.HEALTHS
                    ]
                ),
            ]
        )

        dataJson = {"content": content}
        requests.post(_.WEBHOOK_URL, data=dataJson)

    class HealthCheck:
        RETRY = True
        RESULT = None
        IS_SSL = False
        NOT_AFTER = None

        def __init__(_, target="", statuses=[]):
            _.TARGET = target
            _.STATUSES = [] + statuses  # to allocate new memory address

        def appendResult(_, result):
            _.RESULT = result
            _.STATUSES.append(_.Status(result.status_code))
            _.RETRY = not _.isGood()
            _.IS_SSL = True if re.match(r'https:', result.url) is not None else False

        def appendError(_, error, retry=False):
            _.STATUSES.append(_.Status(message=error))
            _.RETRY = retry

        def isGood(_):
            return any([status.OK for status in _.STATUSES])

        def checkCertificate(_):
            domain = re.match(r'https:\/\/(.*)\/', _.TARGET).group(1)
            query = (domain, 443)

            try:
                # SNI traceable here
                connection = ssl.create_connection(query)
                context = ssl.SSLContext(ssl.PROTOCOL_TLS)
                sock = context.wrap_socket(connection, server_hostname=domain)
                certificate = ssl.DER_cert_to_PEM_cert(sock.getpeercert(True))
            except:
                e = sys.exc_info()[0]
                certificate = ssl.get_server_certificate(query)
            x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, certificate)
            _.NOT_AFTER = datetime.strptime(x509.get_notAfter().decode(), '%Y%m%d%H%M%SZ')

        def getNotAfter(_):
            return _.NOT_AFTER.strftime('%Y-%m-%d') if _.IS_SSL else ''

        def shouldAlert(_, ssl_expires_in):
            now = datetime.now()
            delta = timedelta(days=ssl_expires_in + 1, seconds=1)
            return not _.isGood() or now + delta > _.NOT_AFTER

        def getRemainingDays(_):
            now = datetime.now()
            delta = _.NOT_AFTER - datetime.now()
            return delta.days

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
