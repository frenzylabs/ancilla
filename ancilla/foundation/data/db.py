'''
 db.py
 data

 Created by Wess Cope (me@wess.io) on 09/30/19
 Copyright 2019 Wess Cope
'''

from peewee import SqliteDatabase
from ..env  import Env

class Database(object):
  path = "/".join([Env.ancilla, ".a_store"])
  conn = SqliteDatabase(path, {'foreign_keys' : 1})

  @staticmethod
  def connect():
    Database.conn.connect()
    
  @staticmethod
  def create_tables(tables):
    Database.conn.create_tables(tables)
