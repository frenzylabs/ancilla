'''
 periodic_printer_temp_task.py
 tasks

 Created by Kevin Musselman (kevin@frenzylabs.com) on 02/28/20
 Copyright 2019 FrenzyLabs, LLC.
'''



import time
import sys
import os

from asyncio       import sleep

from .periodic_task import PeriodicTask


class PeriodicPrinterTempTask(PeriodicTask):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, *kwargs)



  async def run_callback(self, payload):
    cnt = 0
    try:
      if self.service.state.temp_updated:
        if time.time() - self.service.state.temp_updated < 3:
          return
      if self.service.state.temp_sent_at:
        if not self.service.state.temp_updated or self.service.state.temp_sent_at > self.service.state.temp_updated:
          return

      cmd = payload.get("command")
      self.service.state.temp_sent_at = time.time()
      print_id = None
      if self.service.current_print:
        print_id = self.service.current_print.id
      self.service.add_command(self.task_id, cnt, cmd, False, skip_queue=True, print_id=print_id)

      await sleep(0.1)
      return {"status": "sent"}


    except Exception as e:
      print(f"Couldnt run Temp Task {self.name}: {str(e)}")
      return {"status": "error", "reason": "Error Running Temp Task"}



