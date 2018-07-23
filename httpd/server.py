#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import datetime
import pathlib
import socket
import select
import logging
import re

IO_BUF_SIZE = 4 * 1 << 10
CLIENT_CLOSE_FLAGS = select.EPOLLERR | select.EPOLLHUP

OK = 200
FORBIDDEN = 403
NOT_FOUND = 404
METHOD_NOT_ALLOWED = 405
INTERNAL_ERROR = 500
STATUS = {
    OK: 'Ok',
    FORBIDDEN: 'Forbidden',
    NOT_FOUND: 'Not Found',
    METHOD_NOT_ALLOWED: 'Method not allowed',
    INTERNAL_ERROR: "Internal Server Error",
}

CONTENT_TYPE = {
    '.html': 'text/html',
    '.css': 'text/css',
    '.js': 'application/javascript',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.swf': 'application/x-shockwave-flash'
}


class Actor(object):
    def __init__(self, server, socket):
        self.server = server
        self.socket = socket
        self.time = time.time()

    def act(self, event):
        pass

    def close(self, event):
        self.socket.shutdown(socket.SHUT_RDWR)
        self.socket.close()

    def process_time(self):
        return (time.time() - self.time) * 1000


class RequestRead(Actor):
    def __init__(self, server, socket):
        super().__init__(server, socket)
        self.status = b''
        self.buffer = b''
        self.server.register(self, self.socket.fileno(), select.EPOLLIN)

    def close(self, event):
        logging.info('CLOSE\t%d; read; buffer: %s; time: %.3f', self.socket.fileno(), self.buffer, self.process_time())
        super().close(event)

    def act(self, event):
        if not event & select.EPOLLIN:
            return

        recieved = self.socket.recv(IO_BUF_SIZE)
        if len(recieved) == 0:
            logging.info('CLOSE\t%d, premature end of read: %s', self.socket.fileno(), self.buffer)
            self.server.unregister(self.socket.fileno())
            self.socket.close()
        else:
            self.buffer += recieved

        end_of_headers = self.buffer.find(b'\r\n\r\n')
        if end_of_headers != -1:
            lines = self.buffer[:end_of_headers].split(b'\r\n')
            self.status = lines.pop(0)
            self.buffer = b''
            RequestWrite(self)


class RequestWrite(Actor):
    def __init__(self, reader):
        super().__init__(reader.server, reader.socket)
        self.file = None
        self.time = reader.time
        self.status = reader.status
        self.page = None

        (self.method, self.uri, self.version) = self.status.split(b'\x20')

        headers = ''

        self.code = INTERNAL_ERROR
        try:
            if self.method in {b'GET', b'HEAD'}:
                match = re.search(b'[\\?#]', self.uri)
                request_path = self.uri[:len(self.uri) if match is None else match.start()]
                parts = []
                for part in request_path.split(b'/'):
                    part = re.sub(b'\\+', b' ', part)
                    part = re.sub(b'%([0-9a-fA-F]{2})', lambda m: bytes.fromhex(m.group(1).decode('ascii')), part)
                    parts.append(part.decode('utf-8'))
                self.page = self.server.root.joinpath(*parts).resolve()

                if self.server.root == self.page or self.server.root in self.page.parents:
                    if self.page.is_dir():
                        self.page = self.page / 'index.html'
                    if self.page.is_file():
                        if self.method == b'GET':
                            self.file = open(str(self.page), 'rb')
                        headers += 'Content-Length: {:d}\r\n'.format(self.page.stat().st_size)
                        if self.page.suffix.lower() in CONTENT_TYPE:
                            headers += 'Content-Type: {:s}\r\n'.format(CONTENT_TYPE[self.page.suffix.lower()])
                        self.code = OK
                    else:
                        self.code = NOT_FOUND
                else:
                    self.code = FORBIDDEN
            else:
                self.code = METHOD_NOT_ALLOWED
        except FileNotFoundError as e:
            logging.exception('File not found: %s', e)
            headers = ''
            self.code = 404
        except Exception as e:
            logging.exception('Internal error: %s', e)
            headers = ''

        buffer = 'HTTP/1.1 {:d} {:s}\r\n'.format(self.code, STATUS[self.code])
        buffer += datetime.datetime.utcnow().strftime('Date: %a, %d %b %Y %H:%M:%S UTC\r\n')
        buffer += 'Server: httpd.py\r\n'
        buffer += 'Connection: close\r\n'
        buffer += headers + '\r\n'

        self.buffer = buffer.encode('ascii')
        self.server.register(self, self.socket.fileno(), select.EPOLLOUT)

    def close(self, event):
        logging.info('CLOSE\t%d; write; request: %s; time: %.3f', self.socket.fileno(), self.status,
                     self.process_time())
        super().close(event)

    def finish(self):
        logging.info('FINISH\t%d; request: %s; page: %s; code: %d; time: %.3f', self.socket.fileno(), self.status,
                     self.page, self.code, self.process_time())
        self.server.unregister(self.socket.fileno())

    def act(self, event):
        if not event & select.EPOLLOUT:
            return

        try:
            sent = self.socket.send(self.buffer[:IO_BUF_SIZE])
        except (ConnectionResetError, BrokenPipeError):
            self.finish()
            return

        self.buffer = self.buffer[sent:]

        if len(self.buffer) == 0 and self.file is not None:
            buffer = self.file.read(IO_BUF_SIZE)
            if len(buffer) == 0:
                self.file.close()
                self.file = None
            else:
                self.buffer = buffer

        if len(self.buffer) == 0 and self.file is None:
            self.finish()
            self.socket.shutdown(socket.SHUT_RDWR)


class HTTPServer:
    def __init__(self, root='.', host='localhost', port=8080):
        self.root = pathlib.Path(root).resolve()
        self.host = host
        self.port = port
        self.socket = None
        self.poll = None
        self.clients = {}

    def register(self, actor, fileno, flags):
        if fileno in self.clients:
            self.poll.modify(fileno, flags | CLIENT_CLOSE_FLAGS)
        else:
            self.poll.register(fileno, flags | CLIENT_CLOSE_FLAGS)
        self.clients[fileno] = actor

    def unregister(self, fileno):
        if fileno == -1:
            return
        if fileno in self.clients:
            del self.clients[fileno]
        self.poll.unregister(fileno)

    def bind(self):
        if self.socket is not None:
            self.close()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM | socket.SOCK_NONBLOCK)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.host, self.port))
        logging.info('BIND\t%d', self.socket.fileno())

    def close(self):
        remove = []
        for fileno, actor in self.clients.items():
            if actor.socket.fileno() != -1:
                remove.append(actor.socket.fileno())
            actor.close(0)
        self.clients = {}

        if self.socket is not None and self.socket.fileno() != -1:
            remove.append(self.socket.fileno())

        if self.poll is not None:
            for fileno in remove:
                self.poll.unregister(fileno)
            self.poll.close()
            self.poll = None

        logging.info('Clients closed')

    def unbind(self):
        if self.socket is not None and self.socket.fileno() != -1:
            self.socket.shutdown(socket.SHUT_RDWR)
            self.socket.close()
        self.socket = None

    def wait(self, timeout=None):
        self.socket.listen()
        logging.info('LISTEN\t%d', self.socket.fileno())

        self.poll = select.epoll()
        self.poll.register(self.socket.fileno(), select.EPOLLIN)
        while True:
            events = self.poll.poll(5)
            logging.info('TICK\t%d; %s', len(events), events)
            for fileno, event in events:
                if fileno == self.socket.fileno():
                    client_socket = None
                    for trynum in range(1, 4):
                        try:
                            client_socket, addr = self.socket.accept()
                            break
                        except BlockingIOError as e:
                            logging.info('ERR\t%d; %s', trynum, e)
                            time.sleep(trynum * 0.01)
                    if client_socket is None:
                        logging.info("ADD\tCan't add connection: %d", len(self.clients))
                    else:
                        logging.info("ADD\t%d; Pending connections: %d", client_socket.fileno(), len(self.clients))
                        RequestRead(self, client_socket)
                elif fileno in self.clients:
                    if event & CLIENT_CLOSE_FLAGS:
                        self.poll.unregister(fileno)
                        self.clients[fileno].close(event)
                        del self.clients[fileno]
                    else:
                        self.clients[fileno].act(event)
                else:
                    logging.info("CLOSE\t%d; Remote; Unknown", fileno)
                    self.poll.unregister(fileno)

            remove = []
            actors = []
            for fileno, actor in self.clients.items():
                actors.append('({:d}, {:.3f})'.format(actor.socket.fileno(), actor.process_time()))
                if actor.process_time() > 1000:
                    if actor.socket.fileno() != -1:
                        self.poll.unregister(fileno)
                        self.clients[fileno].close(event)
                    remove.append(fileno)
            logging.info('ACTORS\t%d: %s', len(actors), actors)
            for fileno in remove:
                del self.clients[fileno]
