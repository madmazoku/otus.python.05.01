#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
from collections import deque
import threading
import logging

IO_BUF_SIZE = 4 * 1 << 10
IO_BUF_MAXSIZE = 4 * IO_BUF_SIZE

class AsyncFileReader(threading.Thread):
    def __init__(self):
        super().__init__()
        self.readers = {}
        self.tasks_set = set()
        self.tasks_queue = deque()
        self.working = True
        self.cv = threading.Condition()

    def finish(self):

        for fileno, desc in self.readers.items():
            with desc['lock']:
                desc['eof'] = True

        with self.cv:
            self.working = False
            self.cv.notify()
        self.join()

        self.tasks_set.clear()
        self.tasks_queue.clear()
        self.readers.clear()

    def register(self, fileno, file):
        desc = {
            'fileno': fileno,
            'file' : file,
            'buffer': b'',
            'read': 0,
            'eof': False,
            'lock': threading.Lock()
        }
        self.readers[fileno] = desc
        with self.cv:
            self.tasks_set.add(fileno)
            self.tasks_queue.append(desc)
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
        
        with desc['lock']:
            buffer = desc['buffer']
            desc['buffer'] = b''

        if desc['eof']:
            del self.readers[fileno]
            return (buffer, True)

        with self.cv:
            if fileno not in self.tasks_set:
                self.tasks_set.add(fileno)
                self.tasks_queue.append(desc)
            self.cv.notify()
            return (buffer, False)

    def run(self):
        while(self.working):
            desc = None
            with self.cv:
                while self.working and not self.tasks_queue:
                    self.cv.wait()
                if not self.working:
                    break
                desc = self.tasks_queue.popleft()

            with desc['lock']:
                buffer = desc['file'].read(IO_BUF_SIZE)
                if len(buffer) == 0:
                    desc['eof'] = True
                else:
                    desc['read'] += len(buffer)
                    desc['buffer'] += buffer

            with self.cv:
                if not desc['eof'] and len(desc['buffer']) < IO_BUF_MAXSIZE:
                    self.tasks_queue.append(desc)
                else:
                    self.tasks_set.remove(desc['fileno'])
