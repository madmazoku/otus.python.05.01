#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
from collections import deque
import threading

IO_BUF_SIZE = 4 * 1 << 10
IO_BUF_MAXSIZE = 10 * 1 << 20


class AsyncFileReader(threading.Thread):
    def __init__(self):
        super().__init__()
        self.readers = {}
        self.tasks = deque()
        self.working = True
        self.cv = threading.Condition()

    def finish(self):
        with self.cv:
            self.working = False
            self.cv.notify()
        self.join()

        self.tasks.clear()
        for fileno, desc in self.readers.items():
            if desc['file'] is not None:
                desc['file'].close()
        self.readers.clear()

    def register(self, fileno, file):
        desc = {
            'fileno': fileno,
            'file' : file,
            'buffer': b'',
            'read': 0,
            'eof': False,
            'locked': False,
            'tasked': False
        }
        self.readers[fileno] = desc
        with self.cv:
            desc['tasked'] = True
            self.tasks.append(desc)
            self.cv.notify()

    def unregister(self, fileno):
        desc = self.readers.get(fileno, None)
        if desc is None:
            return
        with self.cv:
            desc['eof'] = True
            del self.readers[fileno]


    def read(self, fileno):
        desc = self.readers.get(fileno, None)
        if desc is None:
            return (b'', True)
        with self.cv:
            if desc['locked']:
                return (b'', False)

            buffer = desc['buffer']
            eof = desc['eof']
            desc['buffer'] = b''
            if eof:
                del self.readers[fileno]
            elif not desc['tasked']:
                desc['tasked'] = True
                self.tasks.append(desc)
                self.cv.notify()
            return (buffer, eof)

    def run(self):
        while(self.working):
            desc = None
            with self.cv:
                while self.working and not self.tasks:
                    self.cv.wait()
                if not self.working:
                    break
                desc = self.tasks.popleft()
                desc['locked'] = True

            file = desc['file']
            buffer = file.read(IO_BUF_SIZE)
            if len(buffer) == 0:
                desc['eof'] = True
            else:
                desc['read'] += len(buffer)
                desc['buffer'] += buffer
            # time.sleep(0.1)

            with self.cv:
                if desc['eof']:
                    desc['file'].close()
                    desc['file'] = None
                elif len(desc['buffer']) < IO_BUF_MAXSIZE:
                    self.tasks.append(desc)
                else:
                    desc['tasked'] = False
                desc['locked'] = False


if __name__ == "__main__":
    afr = AsyncFileReader()
    try:
        print("start")
        afr.start()
        print("\tstarted")

        b = b''
        file = open("./test.log", "rb")
        while(True):
            bf = file.read()
            print("BF {:d}".format(len(bf)))
            if len(bf) == 0:
                file.close()
                break
            b += bf
        print("B {:d}".format(len(b)))

        file1 = open("./test.log", "rb")
        afr.register(1, file1)

        file2 = open("./test.log", "rb")
        afr.register(2, file2)

        b1 = b''
        b2 = b''

        while file1 is not None or file2 is not None:
            print("read")
            (bf1, eof1) = afr.read(1)
            b1 += bf1
            print("\tbf1: {:d}".format(len(bf1)))
            (bf2, eof2) = afr.read(2)
            b2 += bf2
            print("\tbf2: {:d}".format(len(bf2)))

            if eof1:
                print("\tf1 eof")
                file1 = None
            if eof2:
                print("\tf2 eof")
                file2 = None
            time.sleep(0.5)

        print("B1 {:d}".format(len(b1)))
        print("B2 {:d}".format(len(b2)))

        time.sleep(1)
    except KeyboardInterrupt:
        print("stop")
    finally:
        print("finish")
        afr.finish()
        print("\tfinished")
