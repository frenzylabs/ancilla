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
  conn = SqliteExtDatabase(path, pragmas=(
    ('cache_size', -1024 * 64),  # 64MB page-cache.
    ('journal_mode', 'wal'),  # Use WAL-mode (you should always use this!).
    ('foreign_keys', 1),
    ('threadlocals', True)))
  # conn = SqliteExtDatabase(path, {'foreign_keys' : 1, 'threadlocals': True, 'journal_mode': 'wal'})

  router = None

  @staticmethod
  def connect():    
    # Database.conn = SqliteExtDatabase(Database.path, {'foreign_keys' : 1})
    Database.conn.connect()
    Database.router = Router(Database.conn, migrate_dir=DEFAULT_MIGRATE_DIR)    
    
  @staticmethod
  def run_migrations():
    Database.router.run()

  @staticmethod
  def create_tables(tables):
    Database.conn.create_tables(tables)
