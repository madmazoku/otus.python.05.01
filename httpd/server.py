#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime
import pathlib
import socket
import select

IO_BUF_SIZE = 4# * 1<<10
IO_BUF_MAX_SIZE = 10 * 1<<20
CLIENT_CLOSE_FLAGS = select.EPOLLERR|select.EPOLLHUP|select.EPOLLRDHUP

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
    '.html': 'text/html; charset=UTF-8',
    '.css': 'text/css',
    '.js': 'application/javascript',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.swf': 'application/x-shockwave-flash'
}

class RequestRead:
    def __init__(self, server, socket):
        self.server = server
        self.socket = socket
        self.buffer = b''
        self.server.register(self, self.socket.fileno(), select.EPOLLIN)


    def act(self, event):
        if not event & select.EPOLLIN:
            return
        recieved = self.socket.recv(IO_BUF_SIZE)
        if recieved:
            self.buffer += recieved
            end_of_headers = self.buffer.find(b'\r\n\r\n')
            if end_of_headers != -1:
                lines = self.buffer[:end_of_headers].split(b'\r\n')
                (method, uri, version) = lines[0].split(b'\x20')
                self.buffer = self.buffer[end_of_headers+4:]
                RequestWrite(self.server, self.socket, method, uri)


class RequestWrite:
    def __init__(self, server, socket, method, uri):
        self.server = server
        self.socket = socket
        self.file = None

        headers = ''
        headers += datetime.datetime.utcnow().strftime('Date: %a, %d %b %Y %H:%M:%S UTC\r\n')
        headers += 'Server: httpd.py\r\n'
        headers += 'Connection: close\r\n'

        print('method:', method)
        status = INTERNAL_ERROR
        if method in {b'GET', b'HEAD'}:
            paths = uri.decode('ascii').split('/')
            print('uri:', paths)
            page = self.server.root.joinpath(*paths).resolve()
            if self.server.root not in page.parents:
                status = FORBIDDEN
            else:
                if page.is_dir():
                    page = page / 'index.html'
                if page.is_file():
                    if method == b'GET':
                        self.file = open(str(page), 'rb')
                    print('File:', self.file)
                    headers += 'Content-Length: {:d}\r\n'.format(page.stat().st_size)
                    if page.suffix.lower() in CONTENT_TYPE:
                        headers += 'Content-Type: {:s}\r\n'.format(CONTENT_TYPE[page.suffix.lower()])
                    status = OK
                else:
                    status = NOT_FOUND
        else:
            status = METHOD_NOT_ALLOWED

        status_line = 'HTTP/1.1 {:d} {:s}\r\n'.format(status, STATUS[status])

        buffer = status_line + headers + '\r\n'
        print('Sent:', buffer)
        self.buffer = buffer.encode('ascii')
        self.server.register(self, self.socket.fileno(), select.EPOLLOUT)


    def act(self, event):
        if not event & select.EPOLLOUT:
            return

        sent = self.socket.send(self.buffer[:IO_BUF_SIZE])
        self.buffer = self.buffer[sent:]

        if len(self.buffer) == 0:
            if self.file:
                buffer = self.file.read(IO_BUF_SIZE)
                if buffer is None:
                    self.server.unregister(self.socket.fileno())
                    self.socket.shutdown(socket.SHUT_RDWR)
                else:
                    self.buffer = buffer
            else:
                self.server.unregister(self.socket.fileno())
                self.socket.shutdown(socket.SHUT_RDWR)


class HTTPServer:
    def __init__(self, root = '.', host = 'localhost', port = 8080):
        self.root = pathlib.Path(root).resolve()
        self.host = host
        self.port = port
        self.socket = None
        self.clients = {}
        self.poll = select.epoll()

    def register(self, actor, fileno, flags):
        if fileno in self.clients:
            self.poll.modify(fileno, flags | CLIENT_CLOSE_FLAGS)
        else:
            self.poll.register(fileno, flags | CLIENT_CLOSE_FLAGS)
        self.clients[fileno] = actor

    def unregister(self, fileno):
        if fileno in self.clients:
            del self.clients[fileno]
        self.poll.unregister(fileno)

    def listen(self):
        if self.socket is not None:
            self.close()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM|socket.SOCK_NONBLOCK)
        print('bind to:',self.host, self.port)
        self.socket.bind((self.host, self.port))
        self.socket.listen(0)

    def close(self):
        self.socket.close()
        self.socket = None

    def wait(self, timeout = None):
        self.poll.register(self.socket.fileno(), select.EPOLLIN)
        print('register main socket', self.socket.fileno())
        while True:
            events = self.poll.poll(5)
            for fileno, event in events:
                if fileno == self.socket.fileno():
                    print("connection")
                    try:
                        client_socket, addr = self.socket.accept()
                        RequestRead(self, client_socket)
                    except Exception as e:
                        print("Exception: ", e)
                elif fileno in self.clients:
                    if event & CLIENT_CLOSE_FLAGS:
                        print('client connection lost', fileno, event)
                        self.poll.unregister(fileno)
                        self.clients[fileno].socket.close()
                        del self.clients[fileno]
                    else:
                        self.clients[fileno].act(event)
                else:
                    print('unknown client connection closed', fileno, event)
                    self.poll.unregister(fileno)
