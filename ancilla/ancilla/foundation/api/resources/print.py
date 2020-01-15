'''
 printer.py
 api

 Created by Wess Cope (me@wess.io) on 09/30/19
 Copyright 2019 Wess Cope
'''

from .base          import BaseHandler
from ...data.models import Print

class PrintResource(BaseHandler):
  def get(self, *args, **kwargs):
    prnts = Print.select().order_by(Print.created_at.desc())
    pid = self.get_argument('printer_id', None)
    if pid:
      prnts = prnts.where(Print.printer_id==pid)
    limit = self.get_argument('limit', None)
    if limit:
      prnts = prnts.limit(limit)

    self.write(
      {'prints': [prints.json for prints in prnts]}
    )
    # self.finish()

  # def post(self):
  #   printer = Printer(**self.params)
    
  #   if not printer.is_valid:
  #     self.write_error(400, errors=printer.errors)

  #   printer.save()
  #   self.write(printer.json)

    # self.finish()
