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

from ancilla.foundation.data.models import Print

def migrate(migrator, database, fake=False, **kwargs):
    """Write your migrations here."""
    # database.drop_tables([Printer])

    # migrator.add_index(ServiceAttachment, "parent_id", "attachment_id", unique=True)
    # migrator.add_index(PrinterCommand, "", "device_type", unique=True)
    res = next((c for c in database.get_columns(Print._meta.table_name) if c.name == "description" ), None)
    if not res:
        f = pw.CharField(null=True)
        migrator.add_fields(Print, description=f)



def rollback(migrator, database, fake=False, **kwargs):
    """Write your rollback migrations here."""
    migrator.remove_fields(Print, ["description"])
    

