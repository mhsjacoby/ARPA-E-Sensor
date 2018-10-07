import socket
import threading
import os
import sys
import logging
from datetime import datetime, timedelta
import json
import hpd_sensors
import time
import shutil
import subprocess

# Set logging level and format logging entries.

logging.basicConfig(filename = '/home/pi/server_logfile.log', level = logging.INFO,
                    format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                    datefmt='%d-%m-%Y:%H:%M:%S',)
                               
class Server():
    def __init__(self, debug):
        """
        The server class is the main class, and in this instance, the
        main thread that will be executed.  Once initialized,
        the listening socket is opened and created.

        param: settings <class 'dict'>
                    Contains a listen_port,
                    root document directory,
                    sensor read interval, ....
        """
        self.debug = debug
        self.settings = self.import_server_conf()
        self.host = ''
        self.port = int(self.settings['listen_port'])
        self.root = self.settings['root']
        self.audio_root = self.settings['audio_root']
        self.img_root = self.settings['img_root']
        self.stream_type = self.settings['stream_type']
        self.sensors = hpd_sensors.Sensors(int(self.settings['read_interval']), self.debug)
        self.audio = hpd_sensors.MyAudio(self.audio_root, self.debug)
        self.photo = hpd_sensors.MyPhoto(self.img_root, self.stream_type, self.debug)
        self.create_socket()
        
    def import_server_conf(self):
        """
        This function is used to import the configuration file from the
        server directory.  The settings are saved as key:value pairs
        and returned.

        TODO: Format data as json, similar to client.py
        """
        try:
            with open('/home/pi/Github/server/server_conf.json', 'r') as f:
                conf = json.loads(f.read())
            
            return conf
            
        except Exception as e:
            logging.critical("Unable to read server configuration file.  Exception: {}".format(e))
            logging.critical('Exiting.  System should reboot program')
            sys.exit()

    def create_socket(self):
        """
        Create a socket, listen, and wait for connections.  Upon acceptance
        of a new connection, a new thread class (MyThreadedSocket) is spun off with
        the newly created socket.  The thread closes at the end of execution.
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((self.host, self.port))
            sock.listen(5)
            print("Listen socket created on port: {}".format(self.port))
            self.sock = sock
        except socket.error as e:
            logging.critical('Bind failed.  Exception: {}'.format(e))
            logging.critical('Exiting program.  Program should restart from system')
            sys.exit()
        while True:
            try:
                # accept() method creates a new socket separate from the
                # main listening socket.
                (client_socket, client_address) = self.sock.accept()
                try:
                    if client_socket:
                        thr = MyThreadedSocket(client_socket, client_address, self.settings, self.sensors, self.debug)
                        thr.start()
                        thr.join()
                        print("New connection with: {}".format(client_address))
                except Exception as e:
                    logging.warning('create_socket excepted after socket accepted. Exception: {}'.format(e))
                    if client_socket:
                        client_socket.close()
            except Exception as e:
                logging.warning('create_socket function excepted. Exception: {}'.format(e))


class MyThreadedSocket(threading.Thread):
    """
    Instantiate a new thread to manage socket connection with client.
    A multi-threaded server approach likely is unnecessary, but, it's
    good practice.

    param: socket <class 'socket.socket'>
            A newly created socket created by the listen socket
            upon acceptance of new connection.
    param: address
            IP address of client to respond to
    param: settings <class 'dict'>
            Server configuration settings
    param: sensors <class 'hpd_sensors.Sensors'>
            Pointer to master class of sensors.  Allows thread
            to get readings from sensors to send to client.
    """
    def __init__(self, socket, address, settings, sensors, debug):
        threading.Thread.__init__(self)
        self.client_socket = socket
        self.client_address = address
        self.stream_size = 4096
        self.settings = settings
        self.sensors = sensors
        self.debug = debug
    
    def decode_request(self):
        """
        Each line in the client message is separated by a
        carriage return and newline. The first line is 
        the time the request is sent from the client side.  Additional
        lines specify if client wants env_params, audio directories, or photo
        directories.
        """
        decoded = self.request.split('\r\n')
        self.client_request_time = decoded[0]
        self.client_request = decoded[1]
        if len(decoded) > 2:
            self.dirs_to_delete = decoded[2:]
        
    def send_sensors(self):
        """
        Create dictionary of readings, along with additional meta data
        client_request_time and server_response_time, which may be useful 
        for debugging.  List of all readings is sent as the "Readings".

        return: <class 'bytes'>
                Encoded byte string ready to stream to client
        """
        to_send = {"Client_Request_Time": self.client_request_time,
                   "Server_Response_Time": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                   "Readings": self.sensors.readings}
        return json.dumps(to_send).encode()

    def my_recv_all(self, timeout=2):
        """
        Regardless of message size, ensure that entire message is received
        from client.  Timeout specifies time to wait for additional socket
        stream.  By default, will use socket passed to thread.

        return: <class 'str'>
                A string containing all info sent.
        """
        # try:
        #make socket non blocking
        self.client_socket.setblocking(0)
        
        #total data partwise in an array
        total_data=[]
        data=''
        
        #beginning time
        begin=time.time()
        while 1:
            #if you got some data, then break after timeout
            if total_data and time.time()-begin > timeout:
                break
            
            #if you got no data at all, wait a little longer, twice the timeout
            elif time.time()-begin > timeout*2:
                break
            
            #recv something
            try:
                data = self.client_socket.recv(8192).decode()
                if data:
                    total_data.append(data)
                    #change the beginning time for measurement
                    begin = time.time()
                else:
                    #sleep for sometime to indicate a gap
                    time.sleep(0.1)
            except:
                pass
            # except Exception as e:
            #     logging.warning('Exception occured in my_recv_all inner.  Exception: {}'.format(e))
            #     try:
            #         self.client_socket.close()
            #     except:
            #         pass
        # except Exception as e:
        #     logging.warning('Exception occured in my_recv_all_outer.  Exception: {}'.format(e))
        #     try:
        #         self.client_socket.close()
        #     except:
        #         pass
        
        #join all parts to make final string
        return ''.join(total_data)
    
    def run(self):
        """
        Process client request, send requested information, and ensure
        data has been received and successfully written to disk on the
        client side.  If success, cached list of sensor readings, i.e.
        self.sensor.readings, is reset back to empty (to reduce
        possibility of overloading server memory).
        """
        # Receive all data from new client and decode
        self.request = self.my_recv_all()
        self.decode_request()

        # Process based on information requested by client.
        # Info is either environmental parameters or audio data.
        if self.client_request == "env_params":
            try:
                self.client_socket.sendall(self.send_sensors())

                # Client will respond to whether or not the write
                # to the InfluxDB was successful
                self.request = self.my_recv_all()
                self.decode_request()

                # self.client_request is now either "success" or "not success"
                if self.debug:
                    print("Write to influx: {}".format(self.client_request))
                if self.client_request == "SUCCESS":
                    
                    # clear sensor cache
                    self.sensors.readings = []

                    # respond that cache has been cleared.
                    self.client_socket.sendall("Server: Client write status to InfluxDB: {}. \n\
                                                \tself.readings is now cleared. \n\
                                                \tself.readings= {}".format(self.client_request,
                                                                        self.sensors.readings).encode())
                elif self.client_request == "NOT SUCCESS":
                    # Respond that cache has not been cleared
                    self.client_socket.sendall("Server: Client write status to InfluxDB: {}. \n\
                                                \tself.readings has not been cleared".encode())
                if self.debug:
                    print("self.readings: {}".format(self.sensors.readings))

                # Close socket
                self.client_socket.close()
            except Exception as e:
                logging.warning('env_params excepted.  Exception: {}'.format(e))
                if self.client_socket:
                    try:
                        self.client_socket.close()
                    except Exception as e:
                        logging.info('Unable to close client_socket in env_params.  Socket may already be closed.  Exception: {}'.format(e))
            
        elif self.client_request == "to_remove":
            deleted = []
            try:
                # self.dirs_to_delete is updated in self.decode_request
                for d in self.dirs_to_delete:
                    if os.path.isdir(d):
                        try:
                            shutil.rmtree(d)
                        except:
                            logging.info('Unable to remove dir: {}'.format(d))
                    
                    # Regardless of whether or not it was a directory, if it doesn't exist,
                    # then it is identified as 'deleted'
                    if not os.path.isdir(d):
                        deleted.append(d)
                
                # Respond to client with the number of directories removed,
                # followed by the names of the directories on the pi.
                temp = [str(len(deleted))]
                for d in deleted:
                    if self.debug:
                        print('Deleted: {}'.format(d))
                    temp.append(d)

                logging.info('Deleted {} dirs'.format(len(deleted)))
                logging.info('Dirs deleted: {}'.format(deleted))

                # Messages always seperated by carriage return, newline
                message = '\r\n'.join(temp)

                # Respond to clien
                self.client_socket.sendall(message.encode())

                # Close socket
                self.client_socket.close()
            except Exception as e:
                logging.warning('to_remove excepted.  Exception: {}'.format(e))
                if self.client_socket:
                    try:
                        self.client_socket.close()
                    except Exception as e:
                        logging.info('Unable to close client_socket in to_remove.  Socket may already be closed.  Exception: {}'.format(e))
        
        elif self.client_request == 'restart':
            try:
                dt = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                r = ['Pi to restart service.  Time is: {}'.format(dt)]
                message = '\r\n'.join(r)
                self.client_socket.sendall(message.encode())
                self.client_socket.close()

                time.sleep(10)
                subprocess.run("sudo reboot", shell = True)
                # subprocess.run("sudo service hpd_mobile restart", shell = True)
            except Exception as e:
                logging.warning('restart excepted.  Exception: {}'.format(e))
                if self.client_socket:
                    try:
                        self.client_socket.close()
                    except Exception as e:
                        logging.info('Unable to close client_socket in restart.  Socket may already be closed.  Exception: {}'.format(e))

        elif self.client_request == 'restart_img':
            try:
                dt = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                r = ['Pi to restart UV4L.  Time is: {}'.format(dt)]
                message = '\r\n'.join(r)
                self.client_socket.sendall(message.encode())
                self.client_socket.close()

                # time.sleep(10)
                subprocess.run("sudo reboot", shell = True)
                # subprocess.run("sudo service uv4l_raspicam restart", shell = True)
            except Exception as e:
                logging.warning('restart_img excepted.  Exception: {}'.format(e))
                if self.client_socket:
                    try:
                        self.client_socket.close()
                    except Exception as e:
                        logging.info('Unable to close client_socket in restart_img.  Socket may already be closed.  Exception: {}'.format(e))


        # Make sure socket is closed
        self.client_socket.close()

if __name__=='__main__':
    """
    Upon initialization of the program, the configuration file is read
    in and passed to the Server.  The Server is responsible for gathering
    and caching sensor data until a request is received from a client.
    Depending on the data requested, the Server will either send audio
    data or environmental parameters.
    """
    debug = True
    s = Server(debug)

    
