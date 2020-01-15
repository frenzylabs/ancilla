'''
 kv.py
 ancilla

 Created by Wess Cope (me@wess.io) on 10/22/19
 Copyright 2019 Wess Cope
'''

from playhouse.kv import KeyValue
from ..env        import Env

class Document(KeyValue):
  database    = "/".join([Env.ancilla, ".a_store"])
  table_name  = "documents"
