#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import datetime
import pathlib
import socket
import select
import logging
import re
import collections

from async_file_reader import AsyncFileReader

Response = collections.namedtuple("Response", "status code page buffer file")

IO_BUF_SIZE = 4 * 1 << 10
IO_BUF_MAXSIZE = 10 * 1 << 20
CLIENT_CLOSE_FLAGS = select.EPOLLERR | select.EPOLLHUP
CLIENT_TIMEOUT = 1000
CLIENT_ACCEPT_ERROR_TRIES = 4

END_OF_HEADERS_TERM = b'\r\n\r\n'
END_OF_HEADERS_TERM_LEN = len(END_OF_HEADERS_TERM)

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
    def __init__(self, server, socket, start_time=None):
        self.server = server
        self.socket = socket
        self.time = time.time() if start_time is None else start_time

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
        self.check_index = 0
        self.buffer = b''

    def close(self, event):
        logging.info('CLOSE\t%d; read; buffer: %s; time: %.3f', self.socket.fileno(), self.buffer, self.process_time())
        super().close(event)

    def act(self, event):
        if not event & select.EPOLLIN:
            return

        recieved = self.socket.recv(IO_BUF_SIZE)
        if len(recieved) == 0 or len(self.buffer) > IO_BUF_MAXSIZE:
            logging.info('CLOSE\t%d, premature end of read: %d: %s', self.socket.fileno(), len(self.buffer),
                         self.buffer[:IO_BUF_SIZE])
            self.server.unregister(self.socket.fileno())
            self.socket.close()
        else:
            self.buffer += recieved

        end_of_headers = self.buffer.find(END_OF_HEADERS_TERM, self.check_index)
        if end_of_headers != -1:
            header = self.buffer[:end_of_headers]
            parsed_request_header = self.prepare_response(header)
            self.buffer = b''

            writer = RequestWrite(self, parsed_request_header)
            self.server.register(writer, self.socket.fileno(), select.EPOLLOUT)
        else:
            buffer_len = len(self.buffer)
            self.check_index = 0 if buffer_len < END_OF_HEADERS_TERM_LEN else buffer_len - END_OF_HEADERS_TERM_LEN

    def prepare_response(self, header):
        lines = header.split(b'\r\n')
        status = lines.pop(0)

        (method, uri, version) = status.split(b'\x20')

        headers = ''

        code = INTERNAL_ERROR
        page = None
        file = None
        try:
            if method in {b'GET', b'HEAD'}:
                match = re.search(b'[\\?#]', uri)
                request_path = uri[:len(uri) if match is None else match.start()]
                parts = []
                for part in request_path.split(b'/'):
                    part = re.sub(b'\\+', b' ', part)
                    part = re.sub(b'%([0-9a-fA-F]{2})', lambda m: bytes.fromhex(m.group(1).decode('ascii')), part)
                    parts.append(part.decode('utf-8'))
                page = self.server.root.joinpath(*parts).resolve()

                if self.server.root == page or self.server.root in page.parents:
                    if page.is_dir():
                        page = page / 'index.html'
                    if page.is_file():
                        if method == b'GET':
                            file = open(str(page), 'rb')
                        headers += 'Content-Length: {:d}\r\n'.format(page.stat().st_size)
                        if page.suffix.lower() in CONTENT_TYPE:
                            headers += 'Content-Type: {:s}\r\n'.format(CONTENT_TYPE[page.suffix.lower()])
                        code = OK
                    else:
                        code = NOT_FOUND
                else:
                    code = FORBIDDEN
            else:
                code = METHOD_NOT_ALLOWED
        except FileNotFoundError as e:
            logging.exception('File not found: %s', e)
            headers = ''
            code = 404
        except Exception as e:
            logging.exception('Internal error: %s', e)
            headers = ''

        hdr_buffer = 'HTTP/1.1 {:d} {:s}\r\n'.format(code, STATUS[code])
        hdr_buffer += datetime.datetime.utcnow().strftime('Date: %a, %d %b %Y %H:%M:%S UTC\r\n')
        hdr_buffer += 'Server: httpd.py\r\n'
        hdr_buffer += 'Connection: close\r\n'
        hdr_buffer += headers + '\r\n'
        hdr_buffer = hdr_buffer.encode('ascii')

        return Response(status, code, page, hdr_buffer, file)


class RequestWrite(Actor):
    def __init__(self, reader, parsed_request_header):
        super().__init__(reader.server, reader.socket, reader.time)
        self.status = parsed_request_header.status
        self.code = parsed_request_header.code
        self.page = parsed_request_header.page
        self.buffer = parsed_request_header.buffer
        self.file = parsed_request_header.file

        self.server.afr.register(self.socket.fileno(), self.file)

    def close(self, event):
        logging.info('CLOSE\t%d; write; request: %s; time: %.3f', self.socket.fileno(), self.status,
                     self.process_time())
        super().close(event)

    def finish(self):
        logging.info('FINISH\t%d; request: %s; page: %s; code: %d; time: %.3f', self.socket.fileno(), self.status,
                     self.page, self.code, self.process_time())
        self.server.afr.unregister(self.socket.fileno())
        self.server.unregister(self.socket.fileno())

    def act(self, event):
        if not event & select.EPOLLOUT:
            return

        if len(self.buffer) != 0:
            try:
                sent = self.socket.send(self.buffer[:IO_BUF_SIZE])
                self.buffer = self.buffer[sent:]
                logging.info('sent %d: %d', self.socket.fileno(), sent)
            except (ConnectionResetError, BrokenPipeError):
                self.finish()
                return

        if len(self.buffer) == 0 and self.file is not None:
            (buffer, eof) = self.server.afr.read(self.socket.fileno())
            logging.info('AFR: %d; %s', len(buffer), eof)
            self.buffer = buffer
            if eof:
                self.file = None
            # buffer = self.file.read(IO_BUF_SIZE)
            # if len(buffer) == 0:
            #     self.file.close()
            #     self.file = None
            # else:
            #     self.buffer = buffer

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

        self.afr = AsyncFileReader()
        self.afr.start()

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM | socket.SOCK_NONBLOCK)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.socket.bind((self.host, self.port))
        logging.info('BIND\t%d', self.socket.fileno())
        self.socket.listen()
        logging.info('LISTEN\t%d', self.socket.fileno())

        self.poll = select.epoll()
        self.poll.register(self.socket.fileno(), select.EPOLLIN)

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

        if self.socket is not None and self.socket.fileno() != -1:
            self.socket.shutdown(socket.SHUT_RDWR)
            self.socket.close()
        self.socket = None

        logging.info('Socket released')

        self.afr.finish()


    def process_event(self, fileno, event):
        if fileno == self.socket.fileno():
            client_socket = None
            for trynum in range(1, CLIENT_ACCEPT_ERROR_TRIES):
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
                reader = RequestRead(self, client_socket)
                self.register(reader, client_socket.fileno(), select.EPOLLIN)
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

    def cleanup_clients(self):
        remove = []
        actors = []
        for fileno, actor in self.clients.items():
            actors.append('({:d}, {:.3f})'.format(actor.socket.fileno(), actor.process_time()))
            if actor.process_time() > CLIENT_TIMEOUT:
                if actor.socket.fileno() != -1:
                    self.poll.unregister(fileno)
                    self.clients[fileno].close(0)
                remove.append(fileno)
        logging.info('ACTORS\t%d: %s', len(actors), actors)
        for fileno in remove:
            del self.clients[fileno]

    def wait(self):
        while True:
            events = self.poll.poll(5)
            logging.info('TICK\t%d; %s', len(events), events)
            for fileno, event in events:
                self.process_event(fileno, event)
            self.cleanup_clients()
