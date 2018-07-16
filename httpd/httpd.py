#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import signal
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

    pids = set()

    try:

        if opts.workers == 1:
            logging.info("Wait for connections")
            server.wait()
        else:
            while True:
                while len(pids) < opts.workers:
                    pid = os.fork()
                    if pid == 0:
                        pids = None
                        try:
                            logging.info("Wait for connections")
                            server.wait()
                        except (Exception, KeyboardInterrupt):
                            raise
                    else:
                        pids.add(pid)

                (pid, code) = os.wait()
                logging.info('PROCESS\tchild exited %d : %d', pid, code)
                pids.remove(pid)

    except Exception as e:
        logging.exception('EXC: %s', e)
    except KeyboardInterrupt:
        logging.info("SERVER\tstop")

    server.close()

    if pids is not None:
        for pid in pids:
            (pid, code) = os.waitpid(pid, 0)
            logging.info('PROCESS\tchild exited %d : %d', pid, code)
        pids.clear()
        server.unbind()
