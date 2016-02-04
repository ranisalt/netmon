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
logger.propagate = False
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - [%(levelname)s] %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

class Monitor:
    def __init__(self, expected, auth, message, ratio=0.4, threshold=5):
        self.expected = Bandwidth(download=expected.download * ratio,
                upload=expected.upload * ratio)
        self.message = message
        self.twitter = twitter.Twitter(auth=auth)
        self.warning_count = 0
        self.threshold = threshold
        self.last_tweet = 0

        logger.info('Minimum expected speed: %s/%s' % (
            pyspeedtest.pretty_speed(expected.download),
            pyspeedtest.pretty_speed(expected.upload),))

    def check(self):
        logger.debug('Starting check...')
        speedtest = pyspeedtest.SpeedTest()
        download, upload = speedtest.download(), speedtest.upload()
        logger.info('Speed: %s/%s', pyspeedtest.pretty_speed(download),
            pyspeedtest.pretty_speed(upload))

        if download < self.expected.download or upload < self.expected.upload:
            # updating count outside the else branch ensures only one tweet
            # will be sent in a "bad speed window", that is, it will only tweet
            # again once your speed goes above minimum expected values
            self.warning_count += 1

            logger.warning('Speeds under minimal expected.')

            # wait 10 minutes to issue a tweet and only tweet once every 3 hours
            if self.warning_count == self.threshold and \
                    (self.last_tweet + 3 * 60 * 60) < int(time.time()):
                logger.warning('Sending tweet...')
                self.twitter.statuses.update(status=self.message % {
                    'download': pyspeedtest.pretty_speed(download),
                    'upload': pyspeedtest.pretty_speed(upload),
                })
                self.last_tweet = int(time.time())

        else:
            logger.info('Everything working as expected.')
            self.warning_count = 0

        logger.debug('Finished check.')

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

        logging.info('Speed set to %d bytes.' % (int(speed),))
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
