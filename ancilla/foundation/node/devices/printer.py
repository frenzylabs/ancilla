import threading
import time
import zmq
import os

import json
from tornado.ioloop import IOLoop

from ..zhelpers import zpipe, socket_set_hwm
from ...data.models import Printer as PrinterModel
from ..device import Device
from .serial_connector import SerialConnector
from ...env import Env
from ...data.models import DeviceRequest, PrinterCommand, SliceFile, Print
# from queue import Queue
import asyncio
from functools import partial
from tornado.queues     import Queue
from tornado import gen
from tornado.gen        import coroutine, sleep
from collections import OrderedDict
import struct # for packing integers


class CommandQueue(object):
    current_command = None
    current_expiry = None

    def __init__(self):
        self.queue = OrderedDict()

    def add(self, cmd):
        self.queue.pop(cmd.identifier(), None)
        self.queue[cmd.identifier()] = cmd

    def get_command(self):
      if not self.current_command:
        cid, cmd = self.queue.popitem(False)
        self.current_command = cmd
        self.current_expiry = time.time() + 5000
      return self.current_command 

    def finish_command(self, status="finished"):
      if self.current_command:
        self.current_command.status = status
        self.current_command.save()
      self.current_command = None
      self.current_expiry = None

    def update_expiry(self):
        self.current_expiry = time.time() + 5000

    def __next__(self):
        address, worker = self.queue.popitem(False)
        return address
    

class Printer(Device):
    connector = None
    endpoint = None         # Server identity/endpoint
    identity = None
    alive = True            # 1 if known to be alive
    ping_at = 0             # Next ping at this time
    expires = 0             # Expires at this time
    workers = []
    state = "IDLE"
    print_queued = False
    current_print = None
    task_queue = Queue()
    command_queue = CommandQueue()

    def __init__(self, ctx, name, **kwargs):
        query = PrinterModel.select().where(PrinterModel.name == name).limit(1)
        self.printer = query[0]
        self.record = query[0].json
        self.port = self.record['port']
        self.baud_rate = self.record['baud_rate']

        super().__init__(ctx, name, **kwargs)



    def start(self, *args):
      print("START Printer", flush=True)
      self.connector = SerialConnector(self.ctx, self.identity, self.port, self.baud_rate)
      # self.connector.start()
    
    def connect(self, *args):
      try:
        # if not self.connector:
        #   self.connector = SerialConnector(self.ctx, self.identity, self.port, self.baud_rate)
        # else:
        self.connector.open()
        print("Printer Connect", flush=True)
        self.connector.run()
        return {"sent": "Connect"}
      except Exception as e:
        print(f'Exception Open Conn: {str(e)}')
        self.pusher.send_multipart([self.identity, b'error', str(e).encode('ascii')])

    def stop(self, *args):
      print("Printer Stop", flush=True)
      self.connector.close()

    # def serialcmd(self, *args):
    #   cmd = args[0]

    def reset(self, *args):
      s = self.connector.serial
      # s._reconfigurePort()
      # s.setDTR(True) # Drop DTR
      # time.sleep(0.022)    # Read somewhere that 22ms is what the UI does.
      # s.setDTR(True)

    def flush(self, *args):
      self.connector.serial.flush()

    def sendbreak(self, *args):
      print(f'break = serial = {self.connector.serial}', flush=True)
      self.connector.serial.break_condition
      self.connector.serial.send_break(1.0)
      print(self.connector.serial.break_condition)

    def resetinput(self, *args):
      print(f'serial = {self.connector.serial}', flush=True)
      self.connector.serial.reset_input_buffer()

    def resetoutput(self, *args):
      print(f'serial = {self.connector.serial}', flush=True)
      self.connector.serial.reset_output_buffer()      

    def close(self, *args):
      print("Printer Close", flush=True)
      self.connector.close()

    def on_message(self, msg):
      print("ON MESSAge", msg)  
      # identifier, request_id, cmd, *data = msg

    def process_commands(self):
      # print("INSIDE PROCESS COMMANDS")
      cmd = self.command_queue.get_command()
      if not cmd:
        return
      
      request = cmd.request
      if cmd.status == "pending":
        cmd.status = "running"
        
        self.connector.write(cmd.command.encode('ascii'))
        if cmd.nowait:
          self.command_queue.finish_command()
        else:
          cmd.save()
        
        if cmd.sequence < 1:
          request.status = cmd.status
          request.save()
          self.publish_request(request)
          # self.input_stream.send_multipart([cmd.request_id, cmd.num, b'Sent'])
      # else:
      #   print("CMD is Running")

    def add_command(self, request_id, num, data, nowait=False):
      if type(data) == bytes:
        data = data.decode('utf-8')
      pc = PrinterCommand(request_id=request_id, sequence=num, command=data, printer_id=self.record["id"], nowait=nowait)
      pc.save(force_insert=True)
      self.command_queue.add(pc)
      IOLoop.current().add_callback(self.process_commands)
      return pc

    def on_data(self, data):
      # print("Printer ON DATA", flush=True)

      if not data or len(data) < 3:
        return

      identifier, status, msg = data

      cmd = self.command_queue.current_command
      if cmd:
        # print("INSIDE CMD on data")
        cmdstatus = None
        denmsg = msg.decode('utf-8')
        if status == b'error':
          cmdstatus = "error"
          self.command_queue.finish_command(status="error")
        else:
          if denmsg.startswith("echo:busy:"):
            self.command_queue.update_expiry()
          else:
            cmd.response.append(denmsg)

          if denmsg.startswith("ok"):
            cmdstatus = "finished"
            self.command_queue.finish_command()

        if cmd.sequence < 1 and cmdstatus:
          request = cmd.request
          request.status = cmdstatus
          request.save()
          self.publish_request(request)


        num_s = struct.pack('!q', cmd.sequence)
        self.input_stream.send_multipart([cmd.request_id.encode('ascii'), num_s, msg])
      super().on_data(data)



    def send(self, msg):
      # print("SENDING COMMAND", flush=True)
      # print(msg)
      request_id, action, *lparts = msg
      
      data = b''
      if len(lparts) > 0:
        data = lparts[0]
      
      try:
        request_id = request_id.decode('utf-8')
        action_name = action.decode('utf-8').lower()
        method = getattr(self, action_name)
        if not method:
          return json.dumps({request_id: {'error': f'no action {action} found'}})
        
        res = method(request_id, data)
        if not res:
          res = "sent"
        return json.dumps({request_id: res})

      except Exception as e:
        print(f'Send Exception: {str(e)}', flush=True)
        return json.dumps({request_id: {"error": str(e)}})

    def get_state(self, *args):
      # print(self.connector.serial)
      serialopen = False
      if self.connector and self.connector.serial:
        serialopen = self.connector.serial.is_open

      return {"open": serialopen, "alive": self.connector.alive, "state": self.state }

    def pause(self, *args):
      if self.state == "printing":
        self.state = "paused"
      return {"state": self.state}
      

    def command(self, request_id, data):
      # print("CONNECT WRITE", data)
      if self.connector.alive:
        self.add_command(request_id, -1, data+b'\n')
        # self.connector.write(data+b'\n')
      else:
        return {"failed": "Not Connected"}
      # request = DeviceRequest.get_by_id(request_id)
      # request.state = "Sent"
      # request.save()
      return {"sent": "success"}


    # def file_len(fname):
    #   i = 0
    #   with open(fname) as f:
    #       for i, l in enumerate(f):
    #           pass
    #   return i + 1

    async def _process_tasks(self):
        # print("About to get queue", flush=True)
        async for item in self.task_queue:
          # print('consuming {}...'.format(item))
          (method, request_id, msg) = item
          await method(request_id, msg)


    async def _add_task(self, msg):
      await self.task_queue.put(msg)


    def start_print(self, request_id, data):
      request = DeviceRequest.get_by_id(request_id)
      if self.print_queued:
        request.status = "unschedulable"
        request.save()
        self.publish_request(request)
        return {"error": "Printer Busy"}
      
      loop = IOLoop().current()
      
      self.task_queue.put((self.print_task, request_id, data))
      self.print_queued = True
      loop.add_callback(partial(self._process_tasks))
      self.task_queue.join()

      return {"queued": "success"}

    async def print_task(self, request_id, data):
        request = DeviceRequest.get_by_id(request_id)
        sf = None
        
        try:
          res = data.decode('utf-8')
          content = json.loads(res)
          # print(f"CONTENT = {content}", flush=True)
          fid = content.get("file_id")
          sf = SliceFile.get(fid)
          self.current_print = Print(status="running", request_id=request.id, printer_snapshot=self.record, printer=self.printer, slice_file=sf)
          self.current_print.save(force_insert=True)
        except Exception as e:
          print(f"Cant get file to print {str(e)}", flush=True)
          request.status = "failed"
          request.save()
          self.publish_request(request)
          return

        router = self.ctx.socket(zmq.ROUTER)
        
        encoded_request_id = request_id.encode('ascii')
        router.identity = encoded_request_id
        # print("INSIDE PRINTER TASK = ", request_id)
        socket_set_hwm(router, 1)
        router.setsockopt(zmq.LINGER, 0)

        connect_to = f"ipc://{self.identity.decode('utf-8')}_taskrouter"
        router.connect(connect_to)

        self.state = "printing"

        poller = zmq.Poller()
        poller.register(router, zmq.POLLIN)

        try:
          with open(sf.path, "r") as fp: 
          # with open(f'{Env.ancilla}/gcodes/test.gcode', "r") as fp:
            cnt = 1
            fp.seek(0, os.SEEK_END)
            endfp = fp.tell()
            # print("End File POS: ", endfp)
            fp.seek(0)
            line = fp.readline()
            lastpos = 0
            while self.state == "printing":
              # for line in fp:
              await sleep(0.1)
              pos = fp.tell()
              
              # print("File POS: ", pos)
              if pos == endfp:
                self.state = "finished"
                request.status = "finished"
                request.save()
                self.current_print.status = "finished"      
                self.current_print.save()
                break

              if not line.strip():
                line = fp.readline()
                continue

              print("Line {}, POS: {} : {}".format(cnt, pos, line))    

              is_comment = line.startswith(";")
              pc = self.add_command(request_id, cnt, line.encode('ascii'), is_comment)
              if is_comment:
                cnt += 1
                line = fp.readline()
                continue

              await sleep(0.1)

              while True:
                # pollcnt += 1
                try:                
                  items = dict(poller.poll(2000))
                except:
                  break           # Interrupted

                if router in items:
                  res = router.recv_multipart()                  
                  from_ident, num_s, msg = res
                  # cmdseq = struct.unpack('!q', num_s)[0]
                  # print("cmdseq = ", cmdseq)
                  
                  

                  cc = self.command_queue.current_command
                  # if cc:
                  #   print("COMMANDQUE: ", cc.json)
                  if cc and cc.status == "error":
                    request.status = "failed"
                    request.save()
                    self.state = "print_failed"
                    break
                  
                  if not cc or cc.status == "finished":
                    # if pc.status == "finished":
                    self.current_print.state["pos"] = pos
                    self.current_print.save()
                    line = fp.readline()
                    cnt += 1                  
                    break

                else:
                  await sleep(0.1)
                  # if pollcnt > 20:
                  #   break
            
        except Exception as e:
          request.status = "failed"
          request.save()
          self.current_print.status = "failed"
          self.current_print.save()
          print(f"Print Exception: {str(e)}", flush=True)

        print(f"FINISHED PRINT {self.state}", flush=True)
        self.print_queued = False
        self.current_print = None
        self.publish_request(request)

        

    def publish_request(self, request):
      rj = json.dumps(request.json).encode('ascii')
      self.pusher.send_multipart([self.identity+b'.request', b'request', rj])
            
              
