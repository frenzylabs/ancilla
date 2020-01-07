'''
 db.py
 data

 Created by Wess Cope (me@wess.io) on 09/30/19
 Copyright 2019 Wess Cope
'''

from peewee import SqliteDatabase
from playhouse.sqlite_ext import SqliteExtDatabase
from peewee_migrate import Router
from ..env  import Env
import os

DEFAULT_MIGRATE_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), '../../migrations')
# DEFAULT_MIGRATE_DIR = os.path.join(os, 'migrations')

class Database(object):
  path = "/".join([Env.ancilla, ".a_store"])
  conn = SqliteExtDatabase(path, {'foreign_keys' : 1})
  router = Router(conn, migrate_dir=DEFAULT_MIGRATE_DIR)

  @staticmethod
  def connect():
    # Database.conn.connect()
    pass
    
  @staticmethod
  def run_migrations():
    Database.router.run()

  @staticmethod
  def create_tables(tables):
    Database.conn.create_tables(tables)
