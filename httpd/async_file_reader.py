#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
from collections import deque
import threading
import logging

IO_BUF_SIZE = 4 * 1 << 10
IO_BUF_MAXSIZE = 4 * 1 << 20


class ThreadFileReader(threading.Thread):
    def __init__(self):
        super().__init__()
        self.lock = threading.Lock()

        self.fileno = None
        self.file = None
        self.eof = False
        self.buffer = b''


    def attach(self, fileno, file):
        self.fileno = fileno
        self.file = file
        self.eof = False
        self.buffer = b''

    def release(self):
        self.fileno = None
        self.file = None
        self.eof = False
        self.buffer = b''

    def finish(self):
        with self.lock:
            if not self.eof:
                self.eof = True
        self.join()
        self.file.close()

    def read(self):
        with self.lock:
            buffer = self.buffer
            self.buffer = b''
            return (buffer, self.eof)

    def run(self):
        while(True):
            with self.lock:
                if self.eof:
                    break

                buffer = self.file.read(IO_BUF_SIZE)
                if len(buffer) == 0:
                    self.eof = True
                else:
                    self.buffer += buffer





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
                    pass
                elif len(desc['buffer']) < IO_BUF_MAXSIZE:
                    self.tasks.append(desc)
                else:
                    desc['tasked'] = False
                desc['locked'] = False
                self.cv.notify()
