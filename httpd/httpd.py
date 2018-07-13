#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import os
import logging
from optparse import OptionParser

from server import HTTPServer

if __name__ == "__main__":
    op = OptionParser()
    op.add_option("-a", "--address", action="store", type=str, default="localhost")
    op.add_option("-p", "--port", action="store", type=int, default=8080)
    op.add_option("-l", "--log", action="store", type=str, default=None)
    op.add_option("-w", "--workers", action="store", type=int, default=4)
    op.add_option("-r", "--root", action="store", type=str, default="./")
    (opts, args) = op.parse_args()
    logging.basicConfig(
        filename=opts.log,
        level=logging.INFO,
        format='[%(asctime)s] %(levelname).1s %(process).6d %(message)s',
        datefmt='%Y.%m.%d %H:%M:%S')

    server = HTTPServer(opts.root, opts.address, opts.port)

    logging.info("Starting server at %s" % opts.port)
    server.bind()

    pids = {}
    try:
        while True:
            while len(pids) < opts.workers:
                pid = os.fork()
                if pid == 0:
                    try:
                        logging.info("Wait for connections")
                        server.wait()
                    except (Exception, KeyboardInterrupt) as e:
                        logging.exception('EXC: %s', e)
                        server.close()
                        raise
                else:
                    pids.append(pid)

            for pid in pids:
                logging.info('PROCESS\t%d', pid)
                (pid, code) = os.waitpid(pid, os.WNOHANG)
                logging.info('PROCESS\t\t%d; %d', pid, code)

            time.sleep(0.5)

    except KeyboardInterrupt:
        print("Stop server")

