import logging
import socket
import sys
import time
import threading
import serial
import serial.rfc2217
import zmq


class SerialConnector(object):
  def __init__(self, ctx, name, port, baud_rate, **kwargs):
    self.thread_read = None
    self.identity = name
    self.port = port
    self.baud_rate = baud_rate
    self.alive = False

    # self.baud_rate = 999999999
    # print("BAUD RATE: ", self.baud_rate)
    # ser = serial.serial_for_url(args.SERIALPORT, do_not_open=True)
    # ser.timeout = 3     # required so that the reader thread can exit
    # # reset control line as no _remote_ "terminal" has been connected yet
    # ser.dtr = False
    # ser.rts = False
    self.create_serial()
    # self.serial = serial.Serial(self.port, self.baud_rate, timeout=4.0)
    # self.serial.rts = False
    # self.serial.dtr = True
    

    self.log = logging.getLogger('serial')
    self.ctx = ctx
    
  def create_serial(self):
    # print("create serial", flush=True)
    self.serial = serial.Serial(self.port, self.baud_rate, timeout=2.0)
    # self.serial.xonxoff = False     #disable software flow control
    # self.serial.rtscts = False     #disable hardware (RTS/CTS) flow control
    # self.serial.dsrdtr = False       #disable hardware (DSR/DTR) flow control
    # self.serial.rts = False
    # self.serial.dtr = False
  
  def run(self):
    print("INSIDe RUN")
    # ctx = zmq.Context()
    
    # if not self.serial:
    #   print("NEW SERIAL", flush=True)
    #   self.serial = serial.Serial(self.port, self.baud_rate, timeout=1.0)
    # elif not self.serial.is_open:
    #   print("OPEN SERIAL PORT", flush=True)
    #   self.serial.open()

    self.alive = True
    if not self.thread_read or not self.thread_read.isAlive():
      self.thread_read = threading.Thread(target=self.reader, args=(self.ctx,))
      self.thread_read.daemon = True
      self.thread_read.name = self.identity.decode('utf-8') + '->serial-reader'
      self.thread_read.start()

  def write(self, msg):
    if not self.serial or not self.serial.is_open:      
      return {"error": "Serial Connection is not opened"}

    try:
      self.serial.write(msg)
      return {"success": "ok"}
    except Exception as e:
      print('Serial Writer: {}'.format(e))
      return {"error": "Could Not Write To Serial Port", "reason": str(e)}


  def reader(self, ctx):
      publisher = ctx.socket(zmq.PUSH)
      publisher.connect(f"inproc://{self.identity}_collector")

      """loop forever and copy serial->socket"""
      self.log.debug('reader thread started')
      # self.alive = True
      data = b''
      while self.alive:
          try:
              # print("INSIDE RADER THREAD LOOP", flush=True)
              data = self.serial.read_until(b'\n')
              # data += self.serial.read()
              # print(f"INSIDE READER {data}", flush=True)
              if b'\n' in data:
                  publisher.send_multipart([self.identity+ b'.data_received', b'resp', data])
                  data = b''
          except Exception as e:
              # except socket.error as msg: 
              print('Serial Reader Error: {}'.format(e))
              # probably got disconnected
              # self.serial.close()
              publisher.send_multipart([self.identity + b'.data_received', b'error', str(e).encode('ascii')])
              break
     
      self.alive = False
      try:
        self.serial.close()
        self.serial.__del__()
        self.serial = None
      except Exception as e:
        print('ErrorSerial Reader: {}'.format(e))

      # publisher.close()
      publisher.send_multipart([self.identity+ b'.connection.closed', b'closed', b'{"connected": False}'])
      print('reader thread terminated', flush=True)


  def open(self):
    try:
      if not self.serial or not self.serial.is_open:
        # print(f"OPEN SERIAL {self.alive}", flush=True)
        # self
        self.create_serial()
        return {"status": "success"}
        # self.serial = serial.Serial(self.port, self.baud_rate, timeout=4.0)
      # elif self.serial.is_closed:
      #   print("closeing IS OPEN")
      #   self.close()
    except Exception as e:
      print(f'Serial Open Exception {str(e)}')
      return {"status": "error", "reason": str(e)}
    
    # self.serial.open()
    
  def close(self):
      """Stop copying"""
      print('stopping', flush=True)
      self.alive = False
      if self.thread_read:
          # print("JOIN THREAD", flush=True)
          res = self.thread_read.join(4.0)
          if not self.thread_read.isAlive():
            self.thread_read = None
          # if not res:
          #   self.thread_read.kill()
          # if self

      try:
        # print("CLOSE SERIAL", flush=True)
        if self.serial:
          # self.serial.flush()
          self.serial.reset_input_buffer()
          self.serial.reset_output_buffer()
          self.serial.close()
          del self.serial
          time.sleep(1)
          self.serial = None
        return {"status": "success"}
      except Exception as e:
        print(f"SErail close {str(e)}", flush=True)
        return {"status": "error", "reason": str(e)}
      # finally:
      #   del self.serial
      #   self.serial = None
      
        
      
      # if self.alive:
      
      # self.serial = None

