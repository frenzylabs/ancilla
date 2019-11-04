'''
 printer.py
 api

 Created by Wess Cope (me@wess.io) on 09/30/19
 Copyright 2019 Wess Cope
'''

from .base          import BaseHandler
from ...data.models import Printer

class PrinterResource(BaseHandler):
  def get(self, *args, **kwargs):
    # pr = Printer.select().dicts().get()
    # print(pr)
    for printer in Printer.select():
      print(printer.__data__.get("created_at"))
      print(printer.json, flush=True)
      # printer.de

    self.write(
      {'printers': [printer.json for printer in Printer.select()]}
    )
    self.finish()

  def post(self):
    printer = Printer(**self.params)
    
    if not printer.is_valid:
      self.write_error(400, errors=printer.errors)

    printer.save()
    self.write(printer.json)

    self.finish()
