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

from ...data.db import Database

from ...env import Env

from multiprocessing import Process, Queue, Lock, Pipe
from queue import Empty as QueueEmpty
import multiprocessing as mp
import pickle
import re


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

  conn.connect()
  # res = conn.execute_sql("PRAGMA journal_size_limit = -1;").fetchall()
  # res = conn.execute_sql("PRAGMA wal_autocheckpoint = -1;").fetchall()
  res = conn.execute_sql("PRAGMA wal_checkpoint(TRUNCATE);").fetchall()
  print(f'PROCESS INITIAL WALL CHECKPOINT = {res}', flush=True)
  # res = conn.execute_sql("PRAGMA wal_autocheckpoint;").fetchall()
  

  PrinterCommand._meta.database = conn
  Print._meta.database = conn



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
              # respcommand.save()
              break

            # if respcommand["status"] == "finished":
            if respcommand.status == "finished":
              # current_print.state["pos"] = pos
              # current_print.save()
              # prnt.save()
              Print.update(state=prnt.state).where(Print.id == prnt.id).execute()
              # respcommand.save()
              # cmd_queue.send(('done', respcommand.id))
        elif key == "close":
          running = False

    except Exception as e:
      print(f"RES READ EXCEPTION {type(e).__name__}, {str(e)}", flush=True)
      # cmd_queue.put(("state", {"status": "error", "reason": str(e)}))
      cmd_queue.send(("state", {"status": "error", "reason": str(e)}))

  res = conn.execute_sql("PRAGMA wal_checkpoint(TRUNCATE);").fetchall()
  print(f'WALL CHECKPOINT = {res}')
  # res = conn.execute_sql("PRAGMA wal_autocheckpoint=2000;").fetchall()



class PrintTask(AncillaTask):
  def __init__(self, name, service, payload, *args):
    super().__init__(name, *args)
    # self.request_id = request_id    
    self.service = service
    self.payload = payload
    self.state.update({"name": name, "status": "pending", "model": {}})

    self.logmessage = {"message": ""}

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
    return (cmd.status == "pending" or cmd.status == "busy" or cmd.status == "running")
    # return (self.state.status == "running" and (cmd.status == "pending" or cmd.status == "busy" or cmd.status == "running"))

  def handle_current_commands(self):
    new_command_list = []
    lcmd = None
    for (cmdpos, cmd) in self.current_commands:
      if self.command_active(cmd):
        new_command_list.append((cmdpos, cmd))
      else:
        lcmd = cmd
        if cmd.status == "error":
          self.service.current_print.status = "failed"
          self.state.status = "failed"
          self.state.reason = "Could Not Execute Command: " + cmd.command
          
        elif cmd.status == "finished":          
          self.service.current_print.state["pos"] = cmdpos

    if lcmd:
      self.parent_conn.send(("cmd", self.service.current_print, lcmd))
    self.current_commands = new_command_list



  async def get_temp(self, payload):
    cnt = 0
    try:
      cmd = payload.get("command")
      self.service.add_command(self.task_id, cnt, cmd, False, skip_queue=True, print_id=self.service.current_print.id)
      # self.curcommand = self.service.add_command(self.task_id, cnt, cmd, is_comment, print_id=self.service.current_print.id)
      # current_command = service.add_command(self.task_id, cnt, cmd.encode('ascii'))
      await sleep(0.1)
      return {"status": "sent"}


    except Exception as e:
      print(f"Couldnt run task {self.name}: {str(e)}")
      return {"status": "error", "reason": "Error Running Task"}

  async def run(self, device):
    if not self.service.current_print:
      return {"error": "No Print to send to Printer"}
      
    self.logmessage = {"print_id": self.service.current_print.id, "message": ""}  
    
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

    self.start_time = time.time()  

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
    
    
    # res = Database.conn.execute_sql("PRAGMA journal_size_limit = -1;").fetchall()
    # res = Database.conn.execute_sql("PRAGMA wal_autocheckpoint = -1;").fetchall()
    res = Database.conn.execute_sql("PRAGMA wal_checkpoint(TRUNCATE);").fetchall()
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
        
        self.current_commands = []

        
        # lineregex = re.compile("(([A-Z][\d]+)\s([^;]*))")
        lineregex = re.compile("(([^\s\\n\\r]+)\s?([^;]*))")
        while self.state.status == "running":

          cmd_start_time = time.time()
          pos = fp.tell()
          
          
          if pos == endfp:            
            # print("End File POS: ", pos)
            self.state.status = "finished"            
            break

          # if not line.strip():
          #   line = fp.readline()
          #   continue
          
          # print("Line {}, POS: {} : {}".format(cnt, pos, line))    
          linematch = lineregex.match(line)
          if linematch and len(linematch.groups()) > 1:
            cmd = linematch.group(1)
            command = self.service.add_command(self.task_id, cnt, cmd, False, print_id=self.service.current_print.id)
            self.current_commands.append((pos, command))
            await sleep(0)
            self.handle_current_commands()
            while len(self.current_commands) > 10 and self.state.status == "running":            
              # IOLoop().current().add_callback(self.handle_current_commands)
              await sleep(0.01)
              self.handle_current_commands()
          
          cnt += 1
          line = fp.readline()




          # linecommands = lineregex.findall(line)
          # if len(linecommands) > 0:
          #   for c in linecommands:            
          #     command = self.service.add_command(self.task_id, cnt, c[0], False, print_id=self.service.current_print.id)            
          #     self.current_commands.append((pos, command))
          #     await sleep(0)
          #     self.handle_current_commands()
          #     while len(self.current_commands) > 10 and self.state.status == "running":            
          #       # IOLoop().current().add_callback(self.handle_current_commands)
          #       await sleep(0.01)
          #       self.handle_current_commands()
          #     cnt += 1
          # else:
          #   cnt += 1
            
            
          # line = fp.readline()
          # cnt += 1

          # is_comment = line.startswith(";")
          # if is_comment:
          #   line = fp.readline()
          #   continue

          
          # # self.current_command = self.service.add_command(self.task_id, cnt, line, is_comment, print_id=self.service.current_print.id)
          # command = self.service.add_command(self.task_id, cnt, line, is_comment, print_id=self.service.current_print.id)
          # # cmd_data = self.current_command.__data__
          # # print(f"CurCmd: {self.current_command.command}", flush=True)
          # # IOLoop().current().add_callback(self.handle_current_commands)
          # self.handle_current_commands()

          # # self.current_commands = self.handle_current_commands(current_commands)
          # # print(f'CurCmds: {len(self.service.command_queue.current_commands)} Queu: {len(self.service.command_queue.queue)}')
          # # print(f'CurCmds: {len(self.service.command_queue.current_commands)} Queu: {len(self.service.command_queue.queue)} Current Commands: {self.service.command_queue.current_commands}', flush=True)
          # # await sleep(0)
          # self.current_commands.append((pos, command))

          # if len(self.current_commands) > 2:
          #   await sleep(0)

          # while len(self.current_commands) > 10:            
          #   # IOLoop().current().add_callback(self.handle_current_commands)
          #   await sleep(0.005)
          #   self.handle_current_commands()
          #   # if self.state.status != "running":
          #   #   self.current_command.status = self.state.status
          #   #   break
          #   # current_commands = self.handle_current_commands(current_commands)

          # # if len(current_commands) < 10:
          # line = fp.readline()
          # cnt += 1


        
    except Exception as e:
      self.service.current_print.status = "failed"
      # device.current_print.save()
      self.state.status = "failed"
      self.state.reason = str(e)
      self.service.logger.error(f"Print Exception: {str(e)}")
      # print(f"Print Exception: {str(e)}", flush=True)
    
    self.service.logger.debug('Stop Print Task')


    self.service.logger.debug(f'PT: Current Queue = {self.service.command_queue.queue}')
    self.service.logger.debug(f'PT: Current Commands = {self.current_commands}')
    

    # Wait for command queue to finish unless the status wasn't finished
    # If the status was cancelled or failed we just want to clear the pending queue
    timeout = time.time()
    while self.state.status == "finished" and len(self.current_commands) > 0:
        await sleep(0.1)
        self.handle_current_commands()
        if time.time() - timeout > 10:
          self.logmessage["message"] = f"PrintQueueTimeout: PendingQueue: {self.service.command_queue.queue}, SentQueue: {self.current_commands}"
          self.service.logger.info(self.logmessage)
          break


    self.service.command_queue.queue.clear()
    self.current_commands = [(pos, cmd) for (pos, cmd) in self.current_commands if cmd.status != "pending"]

    self.service.logger.debug(f'Current Commands = {self.service.command_queue.queue}')

    # print(f'Current Commands = {self.service.command_queue.queue}')


    timeout = time.time()
    while len(self.current_commands) > 0:
        await sleep(0.05)
        self.handle_current_commands()
        if time.time() - timeout > 10:
          self.logmessage["message"] = f"PrintQueueTimeout: PendingQueue: {self.service.command_queue.queue}, SentQueue: {self.current_commands}"
          self.service.logger.info(self.logmessage)

          self.service.command_queue.clear()
          break
    # self.service.command_queue.clear()
    
    # res = Database.conn.execute_sql("PRAGMA wal_autocheckpoint=2000;").fetchall()
    # res = Database.conn.execute_sql("PRAGMA wal_checkpoint(TRUNCATE);").fetchall()
    # print(f'Final WALL CHECKPOINT = {res}', flush=True)
    # self.service.create_print_log()
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
    # print(f"FINISHED PRINT {self.state}", flush=True)
    self.logmessage["message"] = f"PrintFinished: {self.state.to_json()}"
    self.service.logger.info(self.logmessage)
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
