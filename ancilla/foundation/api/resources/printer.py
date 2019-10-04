'''
 printer.py
 api

 Created by Wess Cope (me@wess.io) on 09/30/19
 Copyright 2019 Wess Cope
'''

from flask          import Flask, request
from flask_restful  import Resource, Api
from ...data.models import Printer

class PrinterResource(Resource):
  def get(self, id=None):
    if id:
      return Printer.get(Printer.id == id)

    return [printer.json for printer in Printer.select()] or []

  def post(self):
    printer = Printer(**request.json)

    if not printer.is_valid:
      return dict(status="errors", errors=printer.errors), 400

    printer.save()
    
    return printer.json
