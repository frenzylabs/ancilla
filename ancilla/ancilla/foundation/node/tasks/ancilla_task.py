'''
 ancilla_task.py
 ancilla

 Created by Kevin Musselman (kevin@frenzylabs.com) on 01/08/20
 Copyright 2019 FrenzyLabs, LLC.
'''

import time

from tornado.ioloop import IOLoop
# from tornado.gen        import sleep
from functools import partial

from asyncio import sleep

from ...utils.dict import ConfigDict


global TASK_ID
TASK_ID = 0

class AncillaTask(object):
  def __init__(self, name, *args):
      global TASK_ID
      self.name = name
      TASK_ID += 1
      self.task_id = TASK_ID
      self.state = ConfigDict()._make_overlay()
        

  def run(self):
    return



class PeriodicTask(AncillaTask):
  def __init__(self, name, service, payload, *args, **kwargs):
    super().__init__(name, *args)  
    self.service = service
    self.payload = payload

    self.interval = kwargs.get("interval") or 3000
    # self.request_id = request_id
    self.io_loop = IOLoop.current()    
    self.state = "initialized"    
    self.run_count = 0
    self.run_timeout = None
    
  async def run(self, *args):
    # print(f"RUN PERIODIC TASK {self.name}", flush=True)
    if self.state == "initialized":
      self._next_timeout = time.time() + self.interval / 1000.0
      self.run_timeout = self.io_loop.add_timeout(self._next_timeout, partial(self.run_task, args))
      self.state = "pending"
      while self.state != "finished":
        await sleep(5)
      
      if self.run_timeout:
        self.run_timeout.cancel()
      return {"state": self.state}
    else:
      return {"error": "Not initialized"}

  async def run_task(self, *args):
    # print(f"RUN PERIODIC TASK {self.name}", flush=True)
    # if self.state == "initialized":
    #   self._next_timeout = time.time() + self.interval / 1000.0
    #   self.run_timeout = self.io_loop.add_timeout(self._next_timeout, partial(self.run_task, args))
    #   self.state = "pending"
    # el
    if self.state == "running":
      pass
    elif self.state == "pending":
      self.run_count += 1
      self.state = "running"
      # print("is running now", flush=True)
      await self.run_callback(self.payload)

      if self.state != "finished":
        self.state = "pending"
        self._next_timeout = time.time() + self.interval / 1000.0
        self.run_timeout = self.io_loop.add_timeout(self._next_timeout, partial(self.run_task, args))
    else:
      self.run_timeout.cancel()
    return "task"

  async def run_callback(self, payload):
    cnt = 0
    try:
      cmd = payload.get("method")
      self.current_command = device.add_command(self.task_id, cnt, cmd.encode('ascii'))
      while self.command_active():
        await sleep(0.01)
        # if self.current_command == "pending":
        IOLoop.current().add_callback(device.process_commands)

      return {"status": self.current_command.status}

    except Exception as e:
      print(f"Couldnot run task {self.name}: {str(e)}")
      return {"status": "error", "reason": "Error Running Task"}

  def command_active(self):
    if self.state == "running" and (
        self.current_command.status == "pending" or 
        self.current_command.status == "running"):
        return True
    return False


  def stop(self):
    self.state = "finished"
    if self.run_timeout:
      self.run_timeout.cancel()
    # if self.state == ""



