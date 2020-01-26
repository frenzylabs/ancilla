import threading
import time
import sys
import os
import zmq
from zmq.eventloop.zmqstream import ZMQStream
import zmq.asyncio
import json

from tornado.ioloop import IOLoop
from zmq.eventloop.ioloop import PeriodicCallback

import functools
from functools import partial
from asyncio       import sleep

from .ancilla_task import AncillaTask
from ..events.printer import Printer
from ...data.models import Print, PrintSlice, PrinterCommand



from multiprocessing import Process, Queue, Lock, Pipe
from queue import Empty as QueueEmpty
import multiprocessing as mp
import pickle

def pr(l, log):
  l.acquire()
  try:
    print(log, flush=True)
  finally:
      l.release()

def run_save_command(task_id, current_print, cmd_queue):
  from ...env import Env
  from ...data.db import Database
  from playhouse.sqlite_ext import SqliteExtDatabase
  import zmq
  Env.setup()
  conn = SqliteExtDatabase(Database.path, pragmas=(
    # ('cache_size', -1024 * 64),  # 64MB page-cache.
    ('journal_mode', 'wal'),  # Use WAL-mode (you should always use this!).
    ('foreign_keys', 1),
    ('threadlocals', True)))
    # {'foreign_keys' : 1, 'threadlocals': True})
  conn.connect()
  # Database.connect()
  # pr(lock, f'conn = {conn}')
  from ...data.models import Print, PrintSlice, PrinterCommand
  PrinterCommand._meta.database = conn

  # context = zmq.Context()
  # cmd_queue = context.socket(zmq.PULL)
  # cmd_queue.connect("tcp://127.0.0.1:5557")

  start_time = time.time()
  cnt = 1
  running = True
  while running:
    # if cnt == 1:
    #   start_time = time.time()
    if cnt % 100 == 0:
      print(f"PROCESS COMMANDS {cnt} DONE {time.time() - start_time}")
      # running = False
      # break

    try:
      # payload = resp_queue.get()
      payload = None
      polltimeout = 0.0001
      respcommand = None
      # if queuesize >= maxqueuesize:
      #   polltimeout = 10

      # res = cmd_queue.poll(polltimeout)
      # if res:
      payload = cmd_queue.recv()
      # payload = cmd_queue.recv_multipart()
      # queuesize -= 1

      if payload:
        (key, prnt, respcommand) = payload
        # print(f"JSONCMD = {jsoncmd}")
        # respcommand = pickle.loads(pcb)
        # respcommand = PrinterCommand(**jsoncmd)
        if key == "cmd":
          cnt += 1
          # respcommand = json.loads(resp.decode('utf-8'))
          # if cnt % 20 == 0:
          #   print(f"Save command cnt: {cnt} {time.time()}")
          if respcommand:
            # print(f"has resp command {respcommand._meta.database.__dict__}")
            if respcommand.status == "error":
            # if respcommand["status"] == "error":
              respcommand.save()
              
              break

            # if respcommand["status"] == "finished":
            if respcommand.status == "finished":
              # current_print.state["pos"] = pos
              # current_print.save()
              prnt.save()
              respcommand.save()
              # cmd_queue.send(('done', respcommand.id))
        elif key == "close":
          running = False
            # current_print.save()
            # line = fp.readline()
            # cnt += 1                  
            # cmd_end_time = time.time()
    except Exception as e:
      print(f"RES READ EXCEPTION {type(e).__name__}, {str(e)}", flush=True)
      # cmd_queue.put(("state", {"status": "error", "reason": str(e)}))
      cmd_queue.send(("state", {"status": "error", "reason": str(e)}))



class PrintTask(AncillaTask):
  def __init__(self, name, service, payload, *args):
    super().__init__(name, *args)
    # self.request_id = request_id    
    self.service = service
    self.payload = payload
    self.state.update({"name": name, "status": "pending", "model": {}})

    
    # image_collector = self.service.ctx.socket(zmq.SUB)
    # image_collector.bind(f"ipc://printcommand{self.task_id}.ipc")

    # self.image_collector = ZMQStream(image_collector)
    # self.image_collector.linger = 0
    # self.image_collector.on_recv(self.on_data, copy=True)

    # command_url = f"tcp://printcommand{self.task_id}.ipc"
    # a = self.service.ctx.socket(zmq.PAIR)
    # b = self.service.ctx.socket(zmq.PAIR)
    # url = "inproc://%s" % uuid.uuid1()
    # a.bind(command_url)
    # b.connect(command_url)
    # return a, b
    # self.state._add_change_listener(
    #         functools.partial(self.trigger_hook, 'state'))

    # ["wessender", "start_print", {"name": "printit", "file_id": 1}]

  async def run(self, device):
    if not self.service.current_print:
      return {"error": "No Print to send to Printer"}
      
    sf = self.service.current_print.print_slice
    num_commands = -1
    try:

      self.service.state.printing = True
      self.service.current_print.status = "running"
      self.service.current_print.save()
      # self.service.fire_event(Printer.state.changed, self.service.state)

      self.state.status = "running"
      self.state.model = self.service.current_print.json
      self.state.id = self.service.current_print.id
      
      self.service.fire_event(Printer.print.started, self.state)
      # num_commands = file_len(sf.path)
    except Exception as e:
      print(f"Cant get file to print {str(e)}", flush=True)
      self.service.fire_event(Printer.print.failed, {"status": "failed", "reason": str(e)})
      # request.status = "failed"
      # request.save()
      # self.publish_request(request)
      return

    
    # mp.set_start_method('spawn')
    # ctx = mp.get_context('fork')
    ctx = mp.get_context('spawn')
    # cmd_queue = ctx.Queue()
    # resp_queue = ctx.Queue()
    self.parent_conn, child_conn = ctx.Pipe()
    self.p = ctx.Process(target=run_save_command, args=(self.task_id, self.service.current_print, child_conn,))
    self.p.daemon = True
    self.p.start()

    # self.parent_conn = self.service.ctx.socket(zmq.PUSH)
    # self.parent_conn.bind("tcp://127.0.0.1:5557")
    # self.p = ctx.Process(target=run_save_command, args=(self.task_id, self.service.current_print,))
    # self.p.daemon = True
    # self.p.start()

    try:
      with open(sf.path, "r") as fp:
        cnt = 1
        fp.seek(0, os.SEEK_END)
        endfp = fp.tell()
        # print("End File POS: ", endfp)
        self.service.current_print.state["end_pos"] = endfp
        current_pos = self.service.current_print.state.get("pos", 0)
        fp.seek(current_pos)
        line = fp.readline()
        start_time = time.time()
        while self.state.status == "running":
          if cnt % 100 == 0:
            print(f"{cnt} COMMANDS FINISHED AFTER {time.time() - start_time}")
            # self.state.status = "paused"
            # break
          # for line in fp:
          cmd_start_time = time.time()
          pos = fp.tell()
          
          # print("File POS: ", pos)
          if pos == endfp:
            self.state.status = "finished"
            self.service.current_print.status = "finished"
            self.service.current_print.save()
            break

          if not line.strip():
            line = fp.readline()
            continue

          # print("Line {}, POS: {} : {}".format(cnt, pos, line))    

          is_comment = line.startswith(";")
          self.current_command = self.service.add_command(self.task_id, cnt, line, is_comment, print_id=self.service.current_print.id)
          # cmd_data = self.current_command.__data__
          # print(f"CurCmd: {self.current_command.command}", flush=True)
          
          while (self.current_command.status == "pending" or 
                self.current_command.status == "running" or 
                self.current_command.status == "busy"):

            await sleep(0.005)
            if self.state.status != "running":
              self.current_command.status = self.state.status
              break
          
          # cmd_data["status"] = self.current_command.status
          # cmd_data["response"] = self.current_command.response
          # self.parent_conn.send_multipart([b'cmd', f'{pos}'.encode('ascii'),  json.dumps(cmd_data).encode('ascii')], copy=False)
          # self.parent_conn.send_pyobj(("cmd", pos, self.current_command))

          # r = self.parent_conn.recv()          
          # print(f"COMMAND cnt: {cnt} {time.time()} {self.current_command.command} FINISHED {time.time() - cmd_start_time}")
          # IOLoop().current().add_callback(functools.partial(self.save_command, self.current_command))
          
          # print(f'InsidePrintTask curcmd= {self.current_command}', flush=True)
          if self.current_command.status == "error":
            self.service.current_print.status = "failed"
            self.state.status = "failed"
            self.state.reason = "Could Not Execute Command: " + self.current_command.command
            self.parent_conn.send(("cmd", self.service.current_print, self.current_command))
            break

          if self.current_command.status == "finished":
            self.service.current_print.state["pos"] = pos
            # self.service.current_print.save()
            line = fp.readline()
            cnt += 1
            cmd_end_time = time.time()

          self.parent_conn.send(("cmd", self.service.current_print, self.current_command))

        
    except Exception as e:
      self.service.current_print.status = "failed"
      # device.current_print.save()
      self.state.status = "failed"
      self.state.reason = str(e)
      print(f"Print Exception: {str(e)}", flush=True)

    # def cmd_callback(cmd, *args):
    #   # print(f'Iniside Command Callback {cmd}, {args}')      
    #   parent_conn.send(("cmd", cmd))
    #   return True

    # while self.state.status == "running":
    #   current_command = None
    #   try:
    #     # print(f'Parent CURRENT OS = {os.getppid()}')
    #     payload = None
    #     res = parent_conn.poll(0.0001)
        
    #     if res:
    #       payload = parent_conn.recv()
    #     else:
    #       await sleep(0.001)
    #       continue
    #     # payload = cmd_queue.get_nowait()        
    #     # print(f"PCbefore = {payload}")
    #     if payload:
    #       (key, pc) = payload
    #       if key == "state":
    #         self.state.status = pc.get("status")
    #         self.state.reason = pc.get("reason") or ""
    #       elif key == "cmd":
    #         current_command = pc
    #         self.service.command_queue.add(current_command, cmd_callback )
    #         IOLoop.current().add_callback(self.service.process_commands)
    #         # if pc.nowait:
    #         #   # self.service.connector.write(pc.command.encode('ascii'))
    #         #   # pc.status = "finished"
    #         #   self.service.command_queue.add(pc)
    #         #   IOLoop.current().add_callback(self.service.process_commands)
    #         # else:
    #         #   self.service.command_queue.add(pc)
    #         #   IOLoop.current().add_callback(self.service.process_commands)
            
    #         # while (current_command.status == "pending" or 
    #         #           current_command.status == "running" or 
    #         #           current_command.status == "busy"):

    #         #     await sleep(0.001)
    #         #     if self.state.status != "running":
    #         #       current_command.status = self.state.status
    #         #       break
    #         # if current_command.status == "error":
    #         #     current_command.status = "failed"
    #         #     self.state.status = "failed"
    #         #     self.state.reason = "Could Not Execute Command: " + current_command.command
            
    #         # # print(f"RespPC = {pc}")
    #         # # resp_queue.put(("cmd", pickle.dumps(pc)))
    #         # # resp_queue.put(("cmd", current_command))
    #         # parent_conn.send(("cmd", current_command))
    #     else:
    #       await sleep(0.001)
    #   except QueueEmpty:
    #     await sleep(0.001)
    #   except Exception as e:
    #     print(f"Exception {type(e).__name__} {str(e)}")
        


    # print     # prints "[42, None, 'hello']"
    return self.cleanup()


  
  def cleanup(self):
    self.parent_conn.send(("close", '', ''))
    self.p.join(timeout=5)
    self.service.current_print.status = self.state.status
    self.service.current_print.save()
    self.state.model = self.service.current_print.json
    if self.state.status == "failed":
      self.service.fire_event(Printer.print.failed, self.state)  
    elif self.state.status == "finished":
      self.service.fire_event(Printer.print.finished, self.state)  
    elif self.state.status == "cancelled":
      self.service.fire_event(Printer.print.cancelled, self.state)  
    elif self.state.status == "paused":
      self.service.fire_event(Printer.print.paused, self.state)  

    
    self.service.print_queued = False
    if self.service.current_print.status != "paused":
      self.service.current_print = None
    # self.state_callback.stop()
    self.service.fire_event(Printer.print.state.changed, self.state)
    self.service.state.printing = False
    self.service.fire_event(Printer.state.changed, self.service.state)
    print(f"FINISHED PRINT {self.state}", flush=True)
    return {"state": self.state}

  async def run2(self, device):
    # self.state_callback = PeriodicCallback(self.get_state, 3000)
    # self.state_callback.start()
    
    # request = DeviceRequest.get_by_id(self.request_id)
    # self.device = device
    if not self.service.current_print:
      return {"error": "No Print to send to Printer"}
      
    sf = self.service.current_print.print_slice
    num_commands = -1
    try:
      # print(f"CONTENT = {content}", flush=True)
      # fid = self.payload.get("file_id")
      # name = self.payload.get("name") or ""
      # sf = SliceFile.get(fid)
      # device.current_print = Print(name=name, status="running", printer_snapshot=device.record, printer=device.printer, slice_file=sf)
      # device.current_print.save(force_insert=True)   

      self.service.state.printing = True
      self.service.current_print.status = "running"
      self.service.current_print.save()
      # self.service.fire_event(Printer.state.changed, self.service.state)

      self.state.status = "running"
      self.state.model = self.service.current_print.json
      self.state.id = self.service.current_print.id
      
      self.service.fire_event(Printer.print.started, self.state)
      # num_commands = file_len(sf.path)
    except Exception as e:
      print(f"Cant get file to print {str(e)}", flush=True)
      self.service.fire_event(Printer.print.failed, {"status": "failed", "reason": str(e)})
      # request.status = "failed"
      # request.save()
      # self.publish_request(request)
      return


    try:
      with open(sf.path, "r") as fp:
        cnt = 1
        fp.seek(0, os.SEEK_END)
        endfp = fp.tell()
        # print("End File POS: ", endfp)
        self.service.current_print.state["end_pos"] = endfp
        current_pos = self.service.current_print.state.get("pos", 0)
        fp.seek(current_pos)
        line = fp.readline()
        while self.state.status == "running":
          # for line in fp:
          cmd_start_time = time.time()
          pos = fp.tell()
          
          # print("File POS: ", pos)
          if pos == endfp:
            self.state.status = "finished"
            self.service.current_print.status = "finished"
            self.service.current_print.save()
            break

          if not line.strip():
            line = fp.readline()
            continue

          # print("Line {}, POS: {} : {}".format(cnt, pos, line))    

          is_comment = line.startswith(";")
          self.current_command = self.service.add_command(self.task_id, cnt, line, is_comment, print_id=self.service.current_print.id)

          # print(f"CurCmd: {self.current_command.command}", flush=True)
          
          while (self.current_command.status == "pending" or 
                self.current_command.status == "running" or 
                self.current_command.status == "busy"):

            await sleep(0.01)
            if self.state.status != "running":
              self.current_command.status = self.state.status
              break
          
          print(f"COMMAND {self.current_command.command} FINISHED {time.time() - cmd_start_time}", flush=True)
          IOLoop().current().add_callback(functools.partial(self.save_command, self.current_command))
          
          # print(f'InsidePrintTask curcmd= {self.current_command}', flush=True)
          if self.current_command.status == "error":
            self.service.current_print.status = "failed"
            self.state.status = "failed"
            self.state.reason = "Could Not Execute Command: " + self.current_command.command
            break

          if self.current_command.status == "finished":
            self.service.current_print.state["pos"] = pos
            # self.service.current_print.save()
            line = fp.readline()
            cnt += 1                  
            cmd_end_time = time.time()

        
    except Exception as e:
      self.service.current_print.status = "failed"
      # device.current_print.save()
      self.state.status = "failed"
      self.state.reason = str(e)
      print(f"Print Exception: {str(e)}", flush=True)

    self.service.current_print.status = self.state.status
    self.service.current_print.save()
    self.state.model = self.service.current_print.json
    if self.state.status == "failed":
      self.service.fire_event(Printer.print.failed, self.state)  
    elif self.state.status == "finished":
      self.service.fire_event(Printer.print.finished, self.state)  
    elif self.state.status == "cancelled":
      self.service.fire_event(Printer.print.cancelled, self.state)  
    elif self.state.status == "paused":
      self.service.fire_event(Printer.print.paused, self.state)  

    
    self.service.print_queued = False
    if self.service.current_print.status != "paused":
      self.service.current_print = None
    # self.state_callback.stop()
    self.service.fire_event(Printer.print.state.changed, self.state)
    self.service.state.printing = False
    self.service.fire_event(Printer.state.changed, self.service.state)
    print(f"FINISHED PRINT {self.state}", flush=True)
    return {"state": self.state}

  def save_command(self, command, *args):
    # print(f"Save Command {command.command}")
    command.save()

  def cancel(self, *args):
    self.state.status = "cancelled"
    # self.service.current_print
    # self.device.add_command(request_id, 0, 'M0\n', True, True)

  def pause(self, *args):
    self.state.status = "paused"

  def get_state(self):
    st = self.state.to_json()
    self.state.model = self.service.current_print.json
    if st != self.state.to_json():
      self.service.fire_event(Printer.print.state.changed, self.state)
