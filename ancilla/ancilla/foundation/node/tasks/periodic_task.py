'''
 periodic_task.py
 tasks

 Created by Kevin Musselman (kevin@frenzylabs.com) on 02/28/20
 Copyright 2019 FrenzyLabs, LLC.
'''


import time

from tornado.ioloop import IOLoop
from functools import partial

from asyncio import sleep


from .ancilla_task import AncillaTask
from ..response import AncillaError


class PeriodicTask(AncillaTask):
  def __init__(self, name, service, payload, *args, **kwargs):
    super().__init__(name, *args)  
    self.service = service
    self.payload = payload

    # self.interval = payload.get("interval") or 3000
    # self.max_runs = payload.get("max_runs") or -1
    # self.request_id = request_id
    self.io_loop = IOLoop.current()    
    self.state = "initialized"    

    self.run_count = 0
    self.run_timeout = None


  @property
  def payload(self):
    return self._payload

  @payload.setter
  def payload(self, value):
    self._payload = value
    self.interval = value.get("interval") or 3000
    self.max_runs = value.get("max_runs") or -1

    
  async def run(self, *args):
    # print(f"RUN PERIODIC TASK {self.name}", flush=True)
    if self.state == "initialized":
      self._next_timeout = time.time() + self.interval / 1000.0
      self.run_timeout = self.io_loop.add_timeout(self._next_timeout, partial(self.run_task, args))
      self.state = "pending"
      while self.state != "finished":
        await sleep(3)
      
      if self.run_timeout:
        self.run_timeout.cancel()
      return {"state": self.state}
    else:
      return {"error": "Not initialized"}

  async def run_task(self, *args):
    if self.state == "running":
      return
    elif self.state == "pending":
      self.run_count += 1
      self.state = "running"
      # print("is running now", flush=True)
      await self.run_callback(self.payload)

      if self.max_runs > 0 and self.run_count >= self.max_runs:
        self.state = "finished"
        return 
      if self.state != "finished":
        self.state = "pending"
        self._next_timeout = time.time() + self.interval / 1000.0
        self.run_timeout = self.io_loop.add_timeout(self._next_timeout, partial(self.run_task, args))
    else:
      self.run_timeout.cancel()
    return "task"

  async def run_callback(self, payload):
    raise AncillaError(400, "Not Implemented")


  def stop(self):
    self.state = "finished"
    if self.run_timeout:
      self.run_timeout.cancel()
    # if self.state == ""



