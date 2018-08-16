import socket
import threading
import os
import sys
import logging
from datetime import datetime
import re

# Set logging level and format logging entries.
logging.basicConfig(filename = 'server_logfile.log', level = logging.DEBUG,
                    format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                    datefmt='%d-%m-%Y:%H:%M:%S',)

def import_server_conf(config_file):
    """
    This function is used to import the configuration file from the
    server directory.  The settings are saved as key:value pairs
    and returned.
    param: config_file; the name of the configuration file, server.conf
    """
    try:
        with open(config_file, 'r') as f:
            config_params = [line.strip('\n') for line in f if not "#" in line]
            settings = {}
            for setting in config_params:
                if setting != "":
                    k, v = setting.split(" ")
                    settings[k] = v
            return settings
    except:
        logging.CRITICAL("Unable to read server configuration file")
        print("Unable to read server configuration file")
        exit()

class Server():
    def __init__(self, settings):
        """
        The server class is the main class, and in this instance, the
        main thread that will be executed.  Once initialized,
        the listening socket is opened and created.

        param: settings; <class 'dict'>; contains a listen_port,
        root document directory, AND ...
        """
        self.settings = settings
        self.host = ''
        self.port = int(self.settings['listen_port'])
        self.root = self.settings['root']
        self.create_socket()


    def create_socket(self):
        """
        Create a socket, listen, and wait for connections.  Upon acceptance
        of a new connection, a new thread class (Multiple) is spun off with
        the newly created socket.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((self.host, self.port))
        sock.listen(5)
        print("Listen socket created on port: {}".format(self.port))
        self.sock = sock
        while True:
            # accept() method creates a new socket separate from the
            # main listening socket.
            (client_socket, client_address) = self.sock.accept()
            if client_socket:
                thr = Multiple(client_socket, client_address, self.settings)
                thr.start()
                thr.join()
                print("New connection with: {}".format(client_address))

class Multiple(threading.Thread):
    def __init__(self, socket, address, settings):
        threading.Thread.__init__(self)
        self.client_socket = socket
        self.client_address = address
        self.stream_size = 4096 # 4096 bytes
        self.settings = settings
    
    def read_params(self, params):
        vals = []
        for p in params:
            vals.append(p + "_" + self.my_read_adc(p))
        return " ".join(vals)

    def my_read_adc(self, param):
        """
        Code to read in analog signal from raspberry pi
        based on the defined parameter.

        param: param; Basically, one for each parameter that we
        want to measure/read.
        i.e. one of "rh", "temp", "gas", "mic", etc.
        """
        continue

    def decode_request(self, request):
        """
        Each line in the client message is separated by a
        carriage return and newline. The first line is 
        the time the request is sent from the client side.  Each
        additional line defines a parameter of interest on the
        client side.

        param: request; full request sent by client
        """
        decoded = request.decode().split('\r\n')
        client_request_time = decoded[0]
        params = decoded[1:]
        return (client_request_time, params)

    def run(self):
        """
        The run method is called when thr.start() is called.  This
        will in turn call other functions
        """
        request = b''
        partial_request = self.client_socket.recv(self.stream_size)
        while len(partial_request) == self.stream_size:
            # print(len(partial_request))
            request += partial_request
            partial_request = self.client_socket.recv(self.stream_size)
        if len(partial_request) < self.stream_size and len(partial_request) != 0:
            request += partial_request
        client_request_time, params = self.decode_request(request)

        self.client_socket.close()




if __name__=='__main__':
    # Upon initialization of the program, the ws.conf file is read in using the import_ws_conf function.  This
    # function is defined outside of a class so that the settingsDict and settingsKeys variables will be available
    # to the 'Threading' class as well.
    settings = import_server_conf('server.conf')
    print(settings)
    try:
        s = Server(settings)
    except Exception as e:
        logging.CRITICAL(e)
    