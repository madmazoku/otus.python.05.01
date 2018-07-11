#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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
        format='[%(asctime)s] %(levelname).1s %(message)s',
        datefmt='%Y.%m.%d %H:%M:%S')

    server = HTTPServer(opts.root, opts.address, opts.port)

    logging.info("Starting server at %s" % opts.port)
    server.listen()
    try:
        logging.info("Wait for connections")
        server.wait()
    except KeyboardInterrupt:
        print("Stop server")
    server.close()
