import pyev
import os
import sys
import logging
import socket
import signal
import errno

from register import register
from http_parser.parser import HttpParser
from response import HttpResponse

NONBLOCKING = (errno.EAGAIN, errno.EWOULDBLOCK)

class Connection(object):
    '''
        Client connection to an rtb server
    '''
    
    STATE_NOT_CONNECTED = 'CONNECTED'
    STATE_CONNECTING = 'CONNECTING'
    STATE_CONNECTED = 'NOT_CONNECTED'
    STATE_ERROR = 'ERROR'
    STATE_IDLE = 'IDLE'
    
    _id = 1

    def __init__(self, sock, loop, address):
        self.sock = sock
        self.watcher = pyev.Io(
            self.sock, pyev.EV_READ, loop, self.io_cb)
        self.watcher.start()
        self.address = address
        self.state = Connection.STATE_CONNECTED
        self.loop = loop
        self.read_buf = ''
        self.write_buf = ''
        self.id = Connection._id
        Connection._id += 1
        logging.debug("Connection.__init__ id=%d" % self.id)

    def io_cb(self, watcher, revents):
        if revents & pyev.EV_READ:
            self.handle_read()
        else:
            self.handle_write()

    def reset(self, events):
        self.watcher.stop()
        self.watcher.set(self.sock, events)
        self.watcher.start()

    def close(self):
        self.sock.close()
        if self.watcher :
            self.watcher.stop()
            self.watcher = None
        logging.debug("Connection.close - id=%d" % self.id)

    def handle_read(self):
        try:
            logging.debug('Connection.handle_read - id=%d' % self.id)
            b = self.sock.recv(2048)
            logging.debug('Connection.handle_read - received buffer size is %d bytes' % len(b))
            logging.debug('Connection.handle_read - received buffer is : \n%s' % b)
            if not len(b):
                logging.debug('Connection.handle_read - 0 bytes received on %d. closing' %
                              self.id)
                self.close()
                return
            self.read_buf += b
        except socket.error as err:
            if err.args[0] not in NONBLOCKING:
                self.handle_error('%s' % args[1])
            else :
                logging.error('Connection.handle_read - NONBLOCKING event on read : %s' % args[1])
        else:
            # check if we have a full http request
            parser = HttpParser()
            recved = len(self.read_buf)
            nparsed = parser.execute(self.read_buf, recved)
            assert nparsed == recved
            if not parser.is_message_complete():
                # we got a partial request keep on reading
                logging.debug(
                    'Connection.handle_read - partial buffer received : \n%s' % 
                     self.read_buf)
                self.reset(pyev.EV_READ)
            else :
                # we got a full request
                self.read_buf = ''
                # match the verb with URI and call
                # after that register for write to send response
                verb = parser.get_method()
                url = parser.get_path()
                logging.debug('Connection.handle_read - id  %d - method is %s and url %s' % 
                    (self.id, verb, url))
                call, keyword_args = register.get_callable(url, verb)
                if not call :
                    err = HttpResponse()
                    err.status_code = 404
                    err.status_string = 'Not Found'
                    err.headers['Content-Type'] = 'application/txt'                    
                    err.body = 'URI Not Found\r\n'
                    self.write_buf = err.to_string()
                else :        
                    keyword_args['http_request'] = parser
                    logging.debug('Connection.handle_read - kargs=%s' % keyword_args)
                    try :
                        response = call(*[], **keyword_args)
                        self.write_buf = response.to_string()
                    except :
                        err = HttpResponse()
                        err.status_code = 500
                        err.status_string = 'Internal Server Error'
                        err.headers['Content-Type'] = 'application/txt'                    
                        err.body = 'Upsssss.\r\n'
                        self.write_buf = err.to_string()
                logging.debug('Connection.handle_read - requesting write %d' % self.id)
                self.reset(pyev.EV_WRITE)

    def handle_write(self):
        try:
            logging.debug('Connection.handle_write - id=%d' % self.id)
            sent = self.sock.send(self.write_buf)
            logging.debug('Connection.handle_write - id=%d sent :\r\n%s' % 
                            (self.id, self.write_buf[:sent]))
        except socket.error as err:
            if err.args[0] not in NONBLOCKING:
                self.handle_error('Connection.handle_write - %s' % args[1])
            else :
                logging.error(
                    'Connection.handle_write - NONBLOCKING event on write : %s' %
                     self.write_buf)
        else :
            self.write_buf = self.write_buf[sent:]
            if not self.write_buf:
                # all the response buffer was sent, 
                # let's wait for another request
                self.reset(pyev.EV_READ)
            else :
                # there is still some buffer left, 
                # wait for the write event again
                logging.debug('Connection.handle_write - partial buffer sent')
                self.reset(pyev.EV_WRITE)

    def handle_error(self, msg, exc_info=True):
        logging.error("Connection.handle_error - %s" % msg, exc_info=exc_info)
        self.close()


