"""Peewee migrations -- 001_create_device_requests.py.

Some examples (model - class or model name)::

    > Model = migrator.orm['model_name']            # Return model in current state by name

    > migrator.sql(sql)                             # Run custom SQL
    > migrator.python(func, *args, **kwargs)        # Run python code
    > migrator.create_model(Model)                  # Create a model (could be used as decorator)
    > migrator.remove_model(model, cascade=True)    # Remove a model
    > migrator.add_fields(model, **fields)          # Add fields to a model
    > migrator.change_fields(model, **fields)       # Change fields
    > migrator.remove_fields(model, *field_names, cascade=True)
    > migrator.rename_field(model, old_field_name, new_field_name)
    > migrator.rename_table(model, new_table_name)
    > migrator.add_index(model, *col_names, unique=False)
    > migrator.drop_index(model, *col_names)
    > migrator.add_not_null(model, *field_names)
    > migrator.drop_not_null(model, *field_names)
    > migrator.add_default(model, field_name, default)

"""

import datetime as dt
import peewee as pw
from decimal import ROUND_HALF_EVEN


try:
    import playhouse.postgres_ext as pw_pext
except ImportError:
    pass

SQL = pw.SQL

from ancilla.foundation.data.models import Printer, Print, PrinterCommand

def migrate(migrator, database, fake=False, **kwargs):
    """Write your migrations here."""
    # database.drop_tables([Printer])
    database.create_tables([
        Printer,
        Print,
        PrinterCommand
    ])

    # migrator.add_index(PrinterCommand, "", "device_type", unique=True)
    # migrator.add_fields(Printer, device=pw.ForeignKeyField(Device, backref='specific'))



def rollback(migrator, database, fake=False, **kwargs):
    """Write your rollback migrations here."""
    database.drop_tables([
        Printer,
        Print,
        PrinterCommand
    ])


# from ancilla.foundation.data.models import Camera
# from ancilla.foundation.env import Env
# from playhouse.sqlite_ext import SqliteExtDatabase
# from peewee_migrate import Router
# path = "/".join([Env.ancilla, ".a_store"])
# conn = SqliteExtDatabase(path, pragmas=(
#     ('journal_mode', 'wal'),  # Use WAL-mode (you should always use this!).
#     ('foreign_keys', 1),
#     ('threadlocals', True)))
# import os
# migrate_dir = os.path.join(os.getcwd(), 'ancilla/ancilla/migrations')
# router = Router(conn, migrate_dir=migrate_dir)
# # router.rollback("002_create_printer")
# # router.rollback("006_create_node")
