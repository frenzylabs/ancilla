'''
 env.py
 foundation

 Created by Wess Cope (me@wess.io) on 09/30/19
 Copyright 2019 Wess Cope
'''

import os

from pathlib  import Path

class Env(object):
  home    = Path.home()
  ancilla = "/".join([f"{home}", '.ancilla'])

  @staticmethod
  def setup():
    if not os.path.exists(Env.ancilla):
      os.makedirs(Env.ancilla)

  @staticmethod
  def set(key, value):
    if value == None:
      os.environ.unsetenv(key)
      return

    os.environ.putenv(key, value)

  @staticmethod
  def get(key):
    return os.environ.get(key)
