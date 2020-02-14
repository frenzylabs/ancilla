'''
 printer_handler.py
 ancilla

 Created by Kevin Musselman (kevin@frenzylabs.com) on 01/08/20
 Copyright 2019 FrenzyLabs, LLC.
'''

from .data_handler import DataHandler
from ..events.printer import Printer
import json
import re

class PrinterHandler(DataHandler):
  def __init__(self, service, *args):
      self.service = service

      
      ## Test if data is a temperature result
      self.temp_regex = re.compile('(?:ok\s)*([T|B|C]\d*:[^\s\/]+\s*\/.*)')

      # This will allow to get the different temperature into groups 
      # Ex. temp  = "ok T:20.2 /0.0 B:19.1 /0.0 T0:20.2 /0.0 @:0 B@:0 P:19.8 A:26.4"
      # self.temp_regex.findall(temp) -> 
      # [('T', '20.2', '0.0'), ('B', '19.1', '0.0'), ('T0', '20.2', '0.0')]
      # self.temp_regex = re.compile('(?:ok\s)*([T|B|C]\d*):([^\s\/]+)\s*\/([^\s]+)')


  def handle(self, data):
      if not data or len(data) < 3:
        return

      fromidentifier, status, msg = data

      identifier, *rest = fromidentifier.split(b'.')

      newmsg = ""
      decodedmsg = ""
      if type(msg) == bytes:
        decodedmsg = msg.decode('utf-8')
      else:
        decodedmsg = msg

      if len(rest) > 0:
        eventkind = b'.'.join(rest)
      else:
        eventkind = b'data_received'

      if eventkind == b'connection.closed':
        self.service.state.connected = False
        self.service.fire_event(Printer.connection.closed, self.service.state)
        eventkind = b'events.printer.' + eventkind
      else:
        eventkind = b'data.printer.' + eventkind


      # newmsg = msg
      prefix = "echo:"
      if decodedmsg.startswith(prefix):
        newmsg = decodedmsg[len(prefix):]
      else:
        newmsg = decodedmsg

      # if self.printer_temp():
      #   return
      # next((item for item in d.keys() if item.startswith("M1")), None)

      cmd = self.service.command_queue.get_active_command()
      
      
      if not self.printer_temp() and cmd:
        # identifier = identifier + b'.printer.log'
        print(f"INSIDE CMD on data {cmd.command}:  {newmsg}", flush=True)
        cmdstatus = None


        if status == b'error':
          cmdstatus = "error"
          self.service.command_queue.finish_current_command(status="error")
        else:
          if newmsg.startswith("busy:"):
            cmdstatus = "busy"
            self.service.command_queue.update_expiry()
          elif newmsg.startswith("Error:"):
            cmdstatus = "error"
            self.service.command_queue.finish_current_command(status="error")
          else:
            cmdstatus = "running"
            cmd.response.append(newmsg)

          if newmsg.startswith("ok") or newmsg == "k\n":
            cmdstatus = "finished"
            self.service.command_queue.finish_current_command()

        payload = {"status": cmdstatus, "sequence": cmd.sequence, "command": cmd.command, "resp": newmsg, "req_id": cmd.parent_id}
        cmd = None
      else:
        payload = {"status": status.decode('utf-8'), "resp": newmsg}

      
      return [eventkind, identifier, json.dumps(payload).encode('ascii')]


  def printer_temp(self, msg):
    m = self.temp_regex.match(msg)
    if m and len(m.groups()) > 0:
      tempstr = m.group(0)      
      if self.service.current_print:
        self.service.current_print.state["temp"] = tempstr
      self.service.state.temp = tempstr
      return True
    return False

