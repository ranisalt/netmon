#!/usr/bin/env python3
from collections import namedtuple
import json
import logging
import pyspeedtest
from pyspeedtest import pretty_speed as ps
import re
import threading
import time
import twitter

Bandwidth = namedtuple('Bandwidth', ['download', 'upload'])


def configureLogger(level=logging.INFO):
    logger = logging.getLogger(__name__)
    logger.setLevel(level)

    # do not propagate to the root logger - prevent duplicated logging
    logger.propagate = False

    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - [%(levelname)s] %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger  # just in case


class Monitor:
    def __init__(self, expected, auth, message, ratio=0.4, threshold=5):
        self.expected = Bandwidth(download=expected.download * ratio,
                upload=expected.upload * ratio)
        self.message = message
        self.twitter = twitter.Twitter(auth=auth)
        self.warning_count = 0
        self.threshold = threshold
        self.last_tweet = 0

        logger = logging.getLogger(__name__)
        logger.info('Minimum expected speed: %s/%s' % (
            ps(self.expected.download),
            ps(self.expected.upload),))

    def speed_is_low(self, download, upload):
        expected = self.expected
        return download < expected.download or upload < expected.upload

    def time_to_tweet(self):
        wait_until = self.last_tweet + 3 * 60 * 60
        return self.warning_count == self.threshold and \
                wait_until < time.time()

    @staticmethod
    def speedtest():
        speedtest = pyspeedtest.SpeedTest()
        return speedtest.download(), speedtest.upload()

    def check(self):
        logger = logging.getLogger(__name__)

        logger.debug('Starting check...')
        download, upload = Monitor.speedtest()
        sdl, sul = ps(download), ps(upload)
        logger.info('Current speed: %s/%s', sdl, sul)

        if self.speed_is_low(download, upload):
            # updating count before the next branch here ensures only one tweet
            # will be sent in a "bad speed window", that is, it will only tweet
            # again once your speed goes above minimum expected values
            self.warning_count += 1

            logger.warning('Detected bandwidth under minimal expected!')

            # wait 10 minutes to issue a tweet and only tweet once every 3 hours
            if self.time_to_tweet():
                logger.warning('Bandwidth low for too long, sending tweet.')
                tweet = self.message.format(sdl, sul, download=sdl, upload=sul)
                logger.debug('Formatted tweet: %s', tweet)

                # actually send the tweet
                self.twitter.statuses.update(status=tweet)
                self.last_tweet = time.time()

        else:
            logger.debug('Everything working as expected.')
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

        return int(speed)

    configureLogger(logging.DEBUG)

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
