#!/usr/bin/env python

import sys
import time
import signal
import pyhorn
import logging
import requests
import argparse
from random import choice, shuffle
from multiprocessing import Process
from faker import Factory as FakeFactory

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)

class Client(Process):

    def __init__(self, base_url, episode, hb_interval, reqs_per_session):
        Process.__init__(self)
        self.base_url = base_url
        self.episode = episode
        self.hb_interval = hb_interval
        self.reqs_per_session = reqs_per_session
        self.http_session = requests.Session()
        self.user_agent = FakeFactory.create().user_agent()

    def run(self):
        log = logging.getLogger()

        # keyboard interrupt handled in main thread
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        series = str(self.episode['mediapackage']['series'])
        episode_type = self.episode['mediapackage']['type']
        resource = "/%s/%s/%s/%s" % (
            series[:4],
            series[4:6],
            series[6:11],
            episode_type
        )

        req_count = 0

        while True:
            log.info("client %s watching episode %s", self.name, self.episode['id'])
            resp = self.http_session.get(self.base_url,
                                params={
                                    '_method': 'PUT',
                                    'id': self.episode['id'],
                                    'type': 'HEARTBEAT',
                                    'in': 0,
                                    'out': 0,
                                    'playing': "true",
                                    'resource': resource,
                                    '_': str(time.time())
                                },
                                headers={
                                    'User-Agent': self.user_agent
                                })

            req_count += 1
            if req_count == self.reqs_per_session:
                self.http_session.cookies.clear()
                req_count = 0

            interval = choice(range(self.hb_interval)) + 1
            log.info("client %s waiting %d seconds", self.name, interval)
            time.sleep(interval)


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--mh-host", help="Matterhorn engage host")
    parser.add_argument("--mh-user", help="Matterhorn engage API user")
    parser.add_argument("--mh-pass", help="Matterhorn engage API password")
    parser.add_argument("--num-clients", type=int, default=10, help="The number of insert threads")
    parser.add_argument("--hb-interval", type=int, default=30, help="The number of seconds each worker waits between heartbeats")
    parser.add_argument("--reqs-per-session", type=int, default=100, help="Number of requests before client will create new session cookie")
    options = parser.parse_args()

    log = logging.getLogger()

    if options.mh_host is None:
        parser.error("missing host option")

    mh = pyhorn.MHClient(options.mh_host, options.mh_user, options.mh_pass)
    episodes = [x._raw for x in mh.search_episodes(sort='DATE_PUBLISHED_DESC')]

    log.info("starting %d clients", options.num_clients)
    base_url = "%s/usertracking/" % options.mh_host
    clients = [
        Client(base_url, choice(episodes), options.hb_interval, options.reqs_per_session)
        for x in xrange(options.num_clients)
        ]
    for c in clients:
        c.start()

    try:
        while True:
            pass
    except KeyboardInterrupt:
        log.info("Caught KeyboardInterrupt; terminating clients")
        for c in clients:
            c.terminate()
            c.join()

if __name__ == '__main__':
    main()
