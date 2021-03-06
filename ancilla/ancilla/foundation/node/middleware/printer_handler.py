'''
 printer_handler.py
 ancilla

 Created by Kevin Musselman (kevin@frenzylabs.com) on 01/08/20
 Copyright 2019 FrenzyLabs, LLC.
'''

from .data_handler import DataHandler
from ..events.printer import Printer
import json, time, re, os
import time
import logging
from logging.handlers import RotatingFileHandler

from tornado.ioloop import IOLoop

from ...env import Env

class PrinterHandler(DataHandler):
  def __init__(self, service, *args):
      super().__init__(service, *args)

      # self.pos_regex = re.compile('(?:ok\s)*\s*([X|Y|Z]):([\d\.]*)\s*([X|Y|Z]):([\d\.]*\s*).*')
      self.coord_regex = re.compile('\\s*(?:([F|X|Y|Z])(\\d+\\.?\\d*))')
      # self.coord_regex = re.compile('(?:G[0|1]\s).*Z(\d+\.?\d+)):([\d\.]*)\s*)')
      self.pos_regex = re.compile('(?:ok\s)*\s*(([X|Y|Z|E]):([\d\.]*)\s*)')
      # self.pos_regex = re.compile('(?:ok\s)*\s*X:[\d\.]+\s*Y:[\d\.]+\s*Z:[\d\.]+.*')

      ## Test if data is a temperature result
      self.temp_regex = re.compile('(?:ok\s)*\s*([T|B|C]\d*:[^\s\/]+\s*\/.*)')

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

      status = status.decode('utf-8')

      cmd = None
      log_level = logging.INFO
      cmdstatus = None

      if self.printer_temp(newmsg):
      #   return
        
        
        active_commands = self.service.command_queue.current_commands.keys()
        cmdkey = next((item for item in active_commands if item.startswith("M105")), None)
        if cmdkey:
          cmd = self.service.command_queue.current_commands[cmdkey]
        else:
          log_level = logging.DEBUG
      elif self.printer_pos(newmsg):
        active_commands = self.service.command_queue.current_commands.keys()
        cmdkey = next((item for item in active_commands if item.startswith("M114")), None)
        if cmdkey:
          cmd = self.service.command_queue.current_commands[cmdkey]

      else:
        cmd = self.service.command_queue.get_active_command()
      
      # if self.service.current_print and not self.logfp:
        
      #   logdir = "/".join([Env.ancilla, 'prints'])
      #   logpath = "/".join([logdir, f'{self.service.current_print.id}.log'])
      #   if not os.path.exists(logdir):
      #     os.makedirs(logdir)
      #   self.logfp = open(logpath, 'a')
      
      
      

      if status == 'error':
        cmdstatus = "error"
        log_level = logging.ERROR

      
      self.logger.debug(f"CmdQueue = {self.service.command_queue.queue.keys()}")
      self.logger.debug(f"CurrentCmdQueue = {self.service.command_queue.current_commands.keys()}")
      if cmd:
        self.logger.debug(f"CmdRespMsg: {newmsg}")
        self.logger.debug(f"CMD: {cmd.command}")
        # identifier = identifier + b'.printer.log'
        # print(f"INSIDE CMD on data {cmd.command}:  {newmsg}", flush=True)
        
        

        if status == 'error':
          cmdstatus = "error"
          log_level = logging.ERROR
          self.service.command_queue.finish_command(cmd, status="error")
        else:
          if newmsg.startswith("busy:"):
            cmdstatus = "busy"
            log_level = logging.DEBUG
            self.service.command_queue.update_expiry()
          elif newmsg.startswith("Error:"):
            cmdstatus = "error"
            log_level = logging.ERROR
            self.service.command_queue.finish_command(cmd, status="error")
            IOLoop.current().add_callback(self.service.process_commands)
          else:
            cmdstatus = "running"
            cmd.response.append(newmsg)

          if newmsg.startswith("ok"):
            cmdstatus = "finished"
            self.print_coords(cmd.command)
            self.service.command_queue.finish_command(cmd)
            IOLoop.current().add_callback(self.service.process_commands)
          
        payload = {"status": cmdstatus, "sequence": cmd.sequence, "command": cmd.command, "resp": newmsg, "req_id": cmd.parent_id}
      else:
        self.logger.debug(f"OnlyRespMsg: {newmsg}")
        payload = {"status": status, "resp": newmsg}

      self.log_printer_output(log_level, payload)
      return [eventkind, identifier, json.dumps(payload).encode('ascii')]


  def printer_temp(self, msg):
    m = self.temp_regex.match(msg)
    if m and len(m.groups()) > 0:
      tempstr = m.group(1)
      self.service.state.temp = tempstr
      self.service.state.temp_updated = time.time()
      if self.service.current_print:
        self.service.current_print.state["temp"] = tempstr
      return True
    return False

  def printer_pos(self, msg):
    m = self.pos_regex.findall(msg)
    if m and len(m) > 3:
      self.service.state.position = msg
      return True
    return False 

  def print_coords(self, cmd):
    if self.service.current_print:
      if cmd[:2] == "G0" or cmd[:2] == "G1":
        res = self.coord_regex.findall(cmd)
        if not self.service.current_print.state.get("coords"):
          self.service.current_print.state["coords"] = {}
        self.service.current_print.state["coords"].update({k: v for k, v in res})

  def log_printer_output(self, level, msg):
    d = {"message": json.dumps(msg)}
    if self.service.current_print:
      d.update({ "print_id": self.service.current_print.id })
    self.logger.log(level, d)




