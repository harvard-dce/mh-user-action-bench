#!/usr/bin/env python

import sys
import time
import boto3
import logging
import argparse
from faker import Factory
from random import choice, shuffle
from multiprocessing import Process, JoinableQueue
from mysql.connector import connect

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)

parser = argparse.ArgumentParser()

parser.add_argument("--host", default=None, help="The hostname of the MySQL node to connect to")
parser.add_argument("--port", default=None, type=int, help="The port of the MySQL node to connect to")
parser.add_argument("--user", default="root", help="The user of the MySQL node to connect to")
parser.add_argument("--password", default="", help="The password of the MySQL node to connect to")
parser.add_argument("--database", default="matterhorn", help="The database to use")
parser.add_argument("--table", default="mh_user_action", help="The user action table to insert to")
parser.add_argument("--aws-profile", default="test", help="AWS profile to use for cloudwatch metrics")
parser.add_argument("--num-workers", type=int, default=10, help="The number of insert threads")
parser.add_argument("--num-inserts", type=int, default=10000, help="The total number of insert to execute")
parser.add_argument("--interval", type=int, default=30, help="The number of seconds each worker waits between inserts")

options = parser.parse_args()


class Worker(Process):

    def __init__(self, work_queue, metric):
        Process.__init__(self)
        self.work_queue = work_queue
        self.metric = metric
        self.con = connect(
            user=options.user,
            password=options.password,
            host=options.host,
            database=options.database
        )

        self.fake = Factory.create()
        self.session_id = self.fake.pystr(max_chars=25)

        session_insert = ("INSERT INTO mh_user_session "
                          "(session_id,user_ip,user_agent,user_id) "
                          "VALUES (%(session_id)s, %(user_ip)s, %(user_agent)s, 'anonymous')")
        c = self.con.cursor()
        c.execute(session_insert, {
            'session_id': self.session_id,
            'user_ip': self.fake.ipv4(),
            'user_agent': self.fake.user_agent()
        })
        self.con.commit()
        c.close()


    def run(self):
        log = logging.getLogger()
        while True:
            action_id = self.work_queue.get()
            if action_id is None:
                log.info("Nothing left to do for worker %s", self.name)
                self.work_queue.task_done()
                self.con.close()
                break
            try:
                action_insert = "INSERT INTO " + options.table + " " \
                                + "(id,inpoint,outpoint,mediapackage,session_id,created,length,type,playing) " \
                                + "VALUES (%(id)s, %(inpoint)s, %(outpoint)s, %(mediapackage)s, %(session_id)s, %(created)s, 0, %(type)s, 1)"

                c = self.con.cursor()
                start = time.time()
                c.execute(action_insert, {
                    'id': action_id,
                    'inpoint': self.fake.pyint(),
                    'outpoint': self.fake.pyint(),
                    'mediapackage': self.fake.uuid4(),
                    'session_id': self.session_id,
                    'created': self.fake.date_time(),
                    'type': choice(['PLAY','PAUSE','SEEK','HEARTBEAT'])
                })
                log.info("%s inserting action %d", self.name, action_id)
                self.con.commit()
                end = time.time()
                self.metric.put_data(
                    MetricData=[
                        dict(
                            MetricName='UserActionInsert-%s' % options.table,
                            Unit='Seconds',
                            Value=round(end - start, 3)
                        )
                    ])
                c.close()
                time.sleep(choice(range(options.interval)) + 1)
            finally:
                self.work_queue.task_done()


def main():

    log = logging.getLogger()

    con = connect(
        user=options.user,
        password=options.password,
        host=options.host,
        database=options.database
    )
    c = con.cursor()
    c.execute("SELECT MAX(id) + 1 FROM %s" % options.table)
    (next_id,) = c.fetchone()
    next_id = next_id or 1
    con.close()

    boto3.setup_default_session(profile_name=options.aws_profile)
    cloudwatch = boto3.resource('cloudwatch')
    metric = cloudwatch.Metric('mh-user-action-bench', 'UserActionInsert-%s' % options.table)

    work_queue = JoinableQueue()

    log.info("starting %d workers", options.num_workers)
    workers = [Worker(work_queue, metric) for x in xrange(options.num_workers)]
    for w in workers:
        w.start()

    action_ids = range(next_id, next_id + options.num_inserts)
    shuffle(action_ids)
    for id in action_ids:
        work_queue.put(id)

    log.info("poisoning the work queue")
    for i in xrange(options.num_workers):
        work_queue.put(None)
    log.info("joining the work queue")
    work_queue.join()

    log.info("joining the work threads")
    for w in workers:
        w.join()

    log.info("all work complete")

if __name__ == '__main__':
    main()
