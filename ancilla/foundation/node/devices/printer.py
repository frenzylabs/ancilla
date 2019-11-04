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
from ...data.models import DeviceRequest, PrinterCommand
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

    def finish_command(self):
      if self.current_command:
        self.current_command.status = "finished"
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
    task_queue = Queue()
    command_queue = CommandQueue()

    def __init__(self, ctx, name, **kwargs):
        query = PrinterModel.select().where(PrinterModel.name == name).limit(1)
        self.record = query[0].json
        self.port = self.record['port']
        self.baud_rate = self.record['baud_rate']

        super().__init__(ctx, name, **kwargs)

    def stop(self):
      self.agent.stop()

    def on_message(self, msg):
      print("ON MESSAge", msg)  
      identifier, request_id, cmd, *data = msg

    def process_commands(self):
      print("INSIDE PROCESS COMMANDS")
      cmd = self.command_queue.get_command()
      if not cmd:
        return
      
      if cmd.status == "pending":
        cmd.status = "running"
        self.connector.write(cmd.command.encode('ascii'))
        if cmd.nowait:
          self.command_queue.finish_command()
        else:
          cmd.save()
          # self.input_stream.send_multipart([cmd.request_id, cmd.num, b'Sent'])
      else:
        print("COM is Running")

    def add_command(self, request_id, num, data, nowait=False):
      if type(data) == bytes:
        data = data.decode('utf-8')
      pc = PrinterCommand(request_id=request_id, sequence=num, command=data, printer_id=self.record["id"], nowait=nowait)
      pc.save(force_insert=True)
      self.command_queue.add(pc)
      IOLoop.current().add_callback(self.process_commands)
      return pc

    def on_data(self, data):
      print("Printer ON DATA", data)
      identifier, msg = data
      cmd = self.command_queue.current_command
      if cmd:
        # print("INSIDE CMD on data")
        denmsg = msg.decode('utf-8')
        if denmsg.startswith("echo:busy:"):
          self.command_queue.update_expiry()
        else:
          cmd.response.append(denmsg)

        if denmsg.startswith("ok"):
          self.command_queue.finish_command()

        num_s = struct.pack('!q', cmd.sequence)
        self.input_stream.send_multipart([cmd.request_id.encode('ascii'), num_s, msg])
      super().on_data(data)


    def start(self, *args):
      print("START Printer", flush=True)
      self.connector = SerialConnector(self.ctx, self.identity, self.port, self.baud_rate)
      self.connector.start()


    def send(self, msg):
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
        return json.dumps({request_id: res})

      except Exception as e:
        return json.dumps({request_id: {"error": str(e)}})

    def state(self, *args):
      return {"open": self.connector.serial.is_open}

    def pause(self, *args):
      if self.state == "printing":
        self.state = "paused"
      return {"state": self.state}
      

    def command(self, request_id, data):
      # self.input_stream.send_multipart([])
      self.add_command(request_id, 0, data+b'\n')
      # self.connector.write(data+b'\n')
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
        print("About to get queue", flush=True)
        async for item in self.task_queue:
          print('consuming {}...'.format(item))
          (method, request_id, msg) = item
          await method(request_id, msg)


    async def _add_task(self, msg):
      await self.task_queue.put(msg)


    def start_print(self, request_id, data):
      request = DeviceRequest.get_by_id(request_id)
      if self.print_queued:
        request.state = "unschedulable"
        request.save()
        return {"error": "Printer Busy"}
      
      loop = IOLoop().current()
      
      self.task_queue.put((self.print_task, request_id, data))
      self.print_queued = True
      loop.add_callback(partial(self._process_tasks))
      self.task_queue.join()

      return {"queued": "success"}

    async def print_task(self, request_id, msg):
        request = DeviceRequest.get_by_id(request_id)
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

        with open(f'{Env.ancilla}/gcodes/test.gcode', "r") as fp:
          cnt = 0
          fp.seek(0, os.SEEK_END)
          endfp = fp.tell()
          print("End File POS: ", endfp)
          fp.seek(0)
          line = fp.readline()
          while self.state == "printing":
            # for line in fp:
            await sleep(0.1)
            pos = fp.tell()
            # print("File POS: ", pos)
            if pos == endfp:
              self.state = "finished"
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
              pollcnt += 1
              try:                
                items = dict(poller.poll(2000))
              except:
                break           # Interrupted

              if router in items:
                res = router.recv_multipart()
                from_ident, num_s, msg = res
                cmdseq = struct.unpack('!q', num_s)[0]
                print("cmdseq = ", cmdseq)

                cc = self.command_queue.current_command
                # if cc:
                #   print("COMMANDQUE: ", cc.json)

                if not cc or cc.status == "finished":
                  # if pc.status == "finished":
                  line = fp.readline()
                  cnt += 1                  
                  break

              else:
                await sleep(0.1)
                # if pollcnt > 20:
                #   break
