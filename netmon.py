#!/usr/bin/env python3
from collections import namedtuple
import json
import logging
import pyspeedtest
import re
import threading
import time
import twitter

Bandwidth = namedtuple('Bandwidth', ['download', 'upload'])
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class Monitor:
    def __init__(self, expected, auth, message, ratio=1/3, threshold=5):
        self.expected = expected
        self.ratio = ratio
        self.message = message
        self.twitter = twitter.Twitter(auth=auth)
        self.warning_count = 0
        self.threshold = threshold
        self.last_tweet = 0

    def check(self):
        logger.info('Starting check...')
        speedtest = pyspeedtest.SpeedTest()
        download, upload = speedtest.download(), speedtest.upload()
        logger.info('Download speed: %s', pyspeedtest.pretty_speed(download))
        logger.info('Upload speed: %s', pyspeedtest.pretty_speed(upload))

        if download < self.expected.download * self.ratio or \
                upload < self.expected.upload * self.ratio:
            logging.warning('Speeds under minimal expected, sending tweet...')

            # wait 10 minutes to issue a tweet and only tweet once an hour
            if self.warning_count == self.threshold and \
                    (self.last_tweet + 60 * 60) < int(time.time()):
                self.twitter.statuses.update(tweet=self.message % {
                    'download': pyspeedtest.pretty_speed(download),
                    'upload': pyspeedtest.pretty_speed(upload),
                })
                self.last_tweet = int(time.time())

            # updating count outside the else branch ensures only one tweet
            # will be sent in a "bad speed window", that is, it will only tweet
            # again once your speed goes above minimum expected values
            self.warning_count += 1

        else:
            logging.info('Everything working as expected.')
            self.warning_count = 0

        logger.info('Finished check.')

if __name__ == '__main__':
    import argparse

    def human_readable_speed(speed):
        result = re.fullmatch('(?P<value>\d+(\.\d+)?)(?P<unit>[bkmg])?',
                speed, re.IGNORECASE)

        if result is None:
            raise argparse.ArgumentTypeError()

        speed = float(result.group('value'))
        unit = result.group('unit').lower()
        if unit is None:
            unit = 'b'

        if unit == 'k':
            speed *= 1024
        elif unit == 'm':
            speed *= 1024 * 1024
        elif unit == 'g':
            speed *= 1024 * 1024 * 1024

        return int(speed)

    parser = argparse.ArgumentParser()
    parser.add_argument('--download', '-d', type=human_readable_speed,
            metavar='D', required=True)
    parser.add_argument('--upload', '-u', type=human_readable_speed,
            metavar='U', required=True)
    parser.add_argument('--credentials', '-c', metavar='filename', required=True)
    parser.add_argument('--delay', '-s', type=int, metavar='s', default=120)
    parser.add_argument('--message', '-m', required=True)
    args = parser.parse_args()

    expected = Bandwidth(download=args.download, upload=args.upload)

    with open(args.credentials) as auth_file:
        auth_params = json.load(auth_file)
        auth = twitter.OAuth(**auth_params)
    mon = Monitor(expected, auth, args.message)

    while True:
        thread = threading.Thread(target=mon.check)
        thread.start()
        time.sleep(args.delay)
