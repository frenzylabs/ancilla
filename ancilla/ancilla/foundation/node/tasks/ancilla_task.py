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




