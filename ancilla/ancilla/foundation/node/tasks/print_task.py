'''
 print_task.py
 ancilla

 Created by Kevin Musselman (kevin@frenzylabs.com) on 01/08/20
 Copyright 2019 FrenzyLabs, LLC.
'''


import time
import sys
import os
import zmq
from zmq.eventloop.zmqstream import ZMQStream
# import zmq.asyncio
import json

from tornado.ioloop import IOLoop, PeriodicCallback
# from zmq.eventloop.ioloop import PeriodicCallback

import functools
from functools import partial
from asyncio       import sleep

from .ancilla_task import AncillaTask, PeriodicTask
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

# def run_log_commands(task_id, current_print, cmd_queue):
#   from ...env import Env
#   from ...data.db import Database
#   from playhouse.sqlite_ext import SqliteExtDatabase
#   import zmq
#   Env.setup()
#   conn = SqliteExtDatabase(Database.path, pragmas=(
#     # ('cache_size', -1024 * 64),  # 64MB page-cache.
#     ('journal_mode', 'wal'),  # Use WAL-mode (you should always use this!).
#     ('foreign_keys', 1),
#     ('threadlocals', True)))
#     # {'foreign_keys' : 1, 'threadlocals': True})
#   conn.connect()

#   self.root_path = "/".join([Env.ancilla, "services", service.identity.decode('utf-8'), "recordings", self.name])
#   if not os.path.exists(self.root_path):
#       os.makedirs(self.root_path)

def run_save_command(task_id, current_print, cmd_queue):
  from ...env import Env
  from ...data.db import Database
  from playhouse.sqlite_ext import SqliteExtDatabase
  import zmq
  Env.setup()
  conn = SqliteExtDatabase(Database.path, pragmas=(
    ('cache_size', -1024 * 64),  # 64MB page-cache.
    ('journal_mode', 'wal'),  # Use WAL-mode (you should always use this!).
    ('foreign_keys', 1),
    ('threadlocals', True)))
    # {'foreign_keys' : 1, 'threadlocals': True})
  conn.connect()
  res = conn.execute_sql("PRAGMA wal_autocheckpoint=-1;").fetchall()
  res = conn.execute_sql("PRAGMA wal_checkpoint(TRUNCATE);").fetchall()
  print(f'INITIAL WALL CHECKPOINT = {res}', flush=True)
  # res = conn.execute_sql("PRAGMA wal_autocheckpoint;").fetchall()
  
  # from ...data.models import Print, PrintSlice, PrinterCommand
  # PrinterCommand._meta.database = conn
  # Print._meta.database = conn



  start_time = time.time()
  cnt = 1
  running = True
  while running:
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

    except Exception as e:
      print(f"RES READ EXCEPTION {type(e).__name__}, {str(e)}", flush=True)
      # cmd_queue.put(("state", {"status": "error", "reason": str(e)}))
      cmd_queue.send(("state", {"status": "error", "reason": str(e)}))

  res = conn.execute_sql("PRAGMA wal_checkpoint(TRUNCATE);").fetchall()
  print(f'WALL CHECKPOINT = {res}')
  res = conn.execute_sql("PRAGMA wal_autocheckpoint=2000;").fetchall()



class PrintTask(AncillaTask):
  def __init__(self, name, service, payload, *args):
    super().__init__(name, *args)
    # self.request_id = request_id    
    self.service = service
    self.payload = payload
    self.state.update({"name": name, "status": "pending", "model": {}})

    # self.log_path = "/".join([Env.ancilla, "services", service.identity.decode('utf-8'), "prints", self.name])
    # if not os.path.exists(self.log_path):
    #   os.makedirs(self.log_path)

    # M105 // temp
    # M114 // cur position

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

  def command_active(self, cmd):
    return (self.state.status == "running" and (cmd.status == "pending" or cmd.status == "busy" or cmd.status == "running"))

  def handle_current_commands(self):
    new_command_list = []
    for (cmdpos, cmd) in self.current_commands:
      if self.command_active(cmd):
        new_command_list.append((cmdpos, cmd))
      else:
        if cmd.status == "error":
          self.service.current_print.status = "failed"
          self.state.status = "failed"
          self.state.reason = "Could Not Execute Command: " + cmd.command
          
        elif cmd.status == "finished":
          self.service.current_print.state["pos"] = cmdpos


        self.parent_conn.send(("cmd", self.service.current_print, cmd))
    self.current_commands = new_command_list

  # def handle_current_commands(self, current_commands):
  #   new_command_list = []
  #   for (cmdpos, cmd) in current_commands:
  #     if self.command_active(cmd):
  #       new_command_list.append((cmdpos, cmd))
  #     else:
  #       if cmd.status == "error":
  #         self.service.current_print.status = "failed"
  #         self.state.status = "failed"
  #         self.state.reason = "Could Not Execute Command: " + cmd.command
          
  #       elif cmd.status == "finished":
  #         self.service.current_print.state["pos"] = cmdpos


  #       self.parent_conn.send(("cmd", self.service.current_print, cmd))
  #   return new_command_list

  async def get_temp(self, payload):
    cnt = 0
    try:
      cmd = payload.get("command")
      is_comment = cmd.startswith(";")
      self.service.add_command(self.task_id, cnt, cmd, is_comment, skip_queue=True, print_id=self.service.current_print.id)
      # self.curcommand = self.service.add_command(self.task_id, cnt, cmd, is_comment, print_id=self.service.current_print.id)
      # current_command = service.add_command(self.task_id, cnt, cmd.encode('ascii'))
      await sleep(0.1)
      return {"status": "sent"}
      # print(f"TEMP Before = {self.curcommand}", flush=True)
      
      # while self.command_active(self.curcommand):
      #   await sleep(0.1)
      
      # print(f"TEMP= {self.curcommand.status} {self.curcommand.response}", flush=True)

      # if self.curcommand.status == "finished" and len(self.curcommand.response) > 0:
      #   self.service.current_print.state["temp"] = self.curcommand.response[0]
      # return {"status": self.curcommand.status}

    except Exception as e:
      print(f"Couldnot run task {self.name}: {str(e)}")
      return {"status": "error", "reason": "Error Running Task"}

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
      self.state.model = self.service.current_print.to_json(extra_attrs=["print_slice"])
      self.state.id = self.service.current_print.id
      
      self.service.fire_event(Printer.print.started, self.state)
      # num_commands = file_len(sf.path)
    except Exception as e:
      print(f"Cant get file to print {str(e)}", flush=True)
      self.service.fire_event(Printer.print.failed, {"status": "failed", "reason": str(e)})
      return

    self.state_callback = PeriodicCallback(self.get_state, 3000, 0.1)
    self.state_callback.start()

    data = {
      "command": "M105"
    }
    self.temp_task = PeriodicTask(f"temp-{self.service.current_print.name}", self.service, data, interval=6000)
    self.temp_task.run_callback = self.get_temp
    self.service.process.add_task(self.temp_task)


    ctx = mp.get_context('spawn')
    # cmd_queue = ctx.Queue()
    # resp_queue = ctx.Queue()
    self.parent_conn, child_conn = ctx.Pipe()
    self.p = ctx.Process(target=run_save_command, args=(self.task_id, self.service.current_print, child_conn,))
    self.p.daemon = True
    self.p.start()

    res = Print.__meta.database.execute_sql("PRAGMA wal_autocheckpoint=-1;").fetchall()
    res = Print.__meta.database.execute_sql("PRAGMA wal_checkpoint(TRUNCATE);").fetchall()
    print(f'INITIAL WALL CHECKPOINT = {res}', flush=True)

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
        self.start_time = time.time()
        self.current_commands = []

        while self.state.status == "running":

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
          # self.current_command = self.service.add_command(self.task_id, cnt, line, is_comment, print_id=self.service.current_print.id)
          command = self.service.add_command(self.task_id, cnt, line, is_comment, print_id=self.service.current_print.id)
          # cmd_data = self.current_command.__data__
          # print(f"CurCmd: {self.current_command.command}", flush=True)
          # IOLoop().current().add_callback(self.handle_current_commands)
          self.handle_current_commands()

          # self.current_commands = self.handle_current_commands(current_commands)
          print(f'CurCmds: {len(self.service.command_queue.current_commands)} Queu: {len(self.service.command_queue.queue)} Current Commands: {self.service.command_queue.current_commands}', flush=True)
          # await sleep(0)
          self.current_commands.append((pos, command))

          if len(self.current_commands) > 2:
            await sleep(0)

          while len(self.current_commands) > 10:            
            # IOLoop().current().add_callback(self.handle_current_commands)
            await sleep(0.01)
            self.handle_current_commands()
            # current_commands = self.handle_current_commands(current_commands)

          # if len(current_commands) < 10:
          line = fp.readline()
          cnt += 1


          
          # while (self.current_command.status == "pending" or 
          #       self.current_command.status == "running" or 
          #       self.current_command.status == "busy"):

          #   await sleep(0.01)
          #   if self.state.status != "running":
          #     self.current_command.status = self.state.status
          #     break
          
          # # cmd_data["status"] = self.current_command.status
          # # cmd_data["response"] = self.current_command.response
          # # self.parent_conn.send_multipart([b'cmd', f'{pos}'.encode('ascii'),  json.dumps(cmd_data).encode('ascii')], copy=False)
          # # self.parent_conn.send_pyobj(("cmd", pos, self.current_command))

          # # r = self.parent_conn.recv()          
          # # print(f"COMMAND cnt: {cnt} {time.time()} {self.current_command.command} FINISHED {time.time() - cmd_start_time}")
          # # IOLoop().current().add_callback(functools.partial(self.save_command, self.current_command))
          
          # # print(f'InsidePrintTask curcmd= {self.current_command}', flush=True)
          # if self.current_command.status == "error":
          #   self.service.current_print.status = "failed"
          #   self.state.status = "failed"
          #   self.state.reason = "Could Not Execute Command: " + self.current_command.command
          #   self.parent_conn.send(("cmd", self.service.current_print, self.current_command))
          #   break

          # if self.current_command.status == "finished":
          #   self.service.current_print.state["pos"] = pos
          #   # self.service.current_print.save()
          #   line = fp.readline()
          #   cnt += 1
          #   cmd_end_time = time.time()

          # self.parent_conn.send(("cmd", self.service.current_print, self.current_command))

        
    except Exception as e:
      self.service.current_print.status = "failed"
      # device.current_print.save()
      self.state.status = "failed"
      self.state.reason = str(e)
      print(f"Print Exception: {str(e)}", flush=True)
    
    self.service.command_queue.queue.clear()
    self.current_commands = [(pos, cmd) for (pos, cmd) in self.current_commands if cmd.status != "pending"]
    
    timeout = time.time()
    while len(self.current_commands) > 0:
        await sleep(0.05)
        IOLoop().current().add_callback(self.handle_current_commands)
        if time.time() - timeout > 10:
          self.service.command_queue.clear()
          break

    res = Print.__meta.database.execute_sql("PRAGMA wal_autocheckpoint=2000;").fetchall()
    res = Print.__meta.database.execute_sql("PRAGMA wal_checkpoint(TRUNCATE);").fetchall()
    print(f'Final WALL CHECKPOINT = {res}', flush=True)
    return self.cleanup()


  
  def cleanup(self):
    self.parent_conn.send(("close", '', ''))
    self.p.join(timeout=5)
    self.service.current_print.status = self.state.status
    self.service.current_print.save()
    self.state.model = self.service.current_print.to_json(extra_attrs=["print_slice"])
    if self.state.status == "failed":
      self.service.fire_event(Printer.print.failed, self.state)  
    elif self.state.status == "finished":
      self.service.fire_event(Printer.print.finished, self.state)  
    elif self.state.status == "cancelled":
      self.service.fire_event(Printer.print.cancelled, self.state)  
    elif self.state.status == "paused":
      self.service.fire_event(Printer.print.paused, self.state)  

    
    self.temp_task.stop()
    self.state_callback.stop()

    self.service.print_queued = False
    if self.service.current_print.status != "paused":
      self.service.current_print = None
    
    
    self.service.fire_event(Printer.print.state.changed, self.state)
    self.service.state.printing = False
    self.service.fire_event(Printer.state.changed, self.service.state)
    print(f"FINISHED PRINT {self.state}", flush=True)
    return {"state": self.state}


  def cancel(self, *args):
    self.state.status = "cancelled"
    # self.service.current_print
    # self.device.add_command(request_id, 0, 'M0\n', True, True)

  def pause(self, *args):
    self.state.status = "paused"

  def get_state(self):
    # st = self.state.to_json()
    newtime = time.time()
    duration = newtime - self.start_time
    self.service.current_print.duration += duration
    self.start_time = newtime
    self.state.model = self.service.current_print.to_json(extra_attrs=["print_slice"])
    # if st != self.state.to_json():
    self.service.fire_event(Printer.print.state.changed, self.state)
