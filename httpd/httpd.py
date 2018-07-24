#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import signal
import os
import logging
import multiprocessing
from optparse import OptionParser

from server import HTTPServer


def run(root, host, port):
    logging.info("Starting server")
    server = HTTPServer(root, host, port)
    server.bind()
    try:
        server.wait()
    except KeyboardInterrupt:
        logging.info("SERVER\tstop")
    server.close()


if __name__ == "__main__":
    op = OptionParser()
    op.add_option("-a", "--address", action="store", type=str, default="localhost")
    op.add_option("-p", "--port", action="store", type=int, default=8080)
    op.add_option("-l", "--log", action="store", type=str, default=None)
    op.add_option("-w", "--workers", action="store", type=int, default=os.cpu_count())
    op.add_option("-r", "--root", action="store", type=str, default="./")
    (opts, args) = op.parse_args()
    logging.basicConfig(
        filename=opts.log,
        level=logging.INFO,
        format="[%(asctime)s] %(levelname).1s %(process).6d %(message)s",
        datefmt="%Y.%m.%d %H:%M:%S")

    logging.info("Starting watcher")

    processes = {}
    try:
        while True:
            while len(processes) < opts.workers:
                p = multiprocessing.Process(
                    target=run, kwargs={
                        "root": opts.root,
                        "host": opts.address,
                        "port": opts.port
                    })
                p.start()
                logging.info("PROCESS\t new child created: %d", p.pid)
                processes[p.pid] = p
            remove_processes = []
            for pid, p in processes.items():
                if not p.is_alive():
                    logging.info("PROCESS\t child exited: %d, %d", pid, p.exitcode)
                    remove_processes.append(pid)
            for pid in remove_processes:
                del processes[pid]
            time.sleep(0.5)
    except Exception as e:
        logging.exception("EXC: %s", e)
    except KeyboardInterrupt:
        logging.info("WATCHER\tstop")
    finally:
        for pid, p in processes.items():
            logging.info("PROCESS\tjoin %d", pid)
            p.join()
