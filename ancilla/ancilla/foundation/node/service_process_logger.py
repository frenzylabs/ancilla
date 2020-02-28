'''
 service_process.py
 ancilla

 Created by Kevin Musselman (kevin@frenzylabs.com) on 01/29/20
 Copyright 2019 FrenzyLabs, LLC.
'''



import logging
import sys
import time
import zmq
import importlib

import os

import json
from datetime import datetime
import sys, logging
from logging import getLoggerClass, addLevelName, setLoggerClass, NOTSET

from logging.handlers import RotatingFileHandler
from pythonjsonlogger import jsonlogger


class DataJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super(DataJsonFormatter, self).add_fields(log_record, record, message_dict)
        if not log_record.get('timestamp'):
            # this doesn't use record.created, so it is slightly off
            now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            log_record['timestamp'] = now
        if log_record.get('level'):
            log_record['level'] = log_record['level'].upper()
        else:
            log_record['level'] = record.levelname


class ServiceProcessLogger(getLoggerClass()):

  def __init__(self, name):
        super().__init__(name)
        self.log_handlers = {}
        self.model = None


  def setup_logger(self, service_model=None):
    if not service_model:
      if not self.model:
        return
    else:
      self.model = service_model


    log_config = self.model.configuration.get("logging", {})
    log_dir     = log_config.get("directory", None)

    default_file_config = {"on": True, "level": "INFO", "maxBytes": 16_000_000, "backupCount": 5}

    log_settings  = self.model.settings.get("logging", {})
    log_level     = log_settings.get("level", "INFO")
    stdout_log    = log_settings.get("stdout", {})
    file_log      = log_settings.get("file", default_file_config)


    log_to_stdout  = stdout_log.get("on", False)
    log_to_file    = file_log.get("on", False)

    
    self.setLevel(log_level)

    min_level = self.level

    self.remove_handler("stdout")
    if log_to_stdout:
      stdout_level   = self.get_int_level(stdout_log.get("level", logging.WARNING))
      min_level = min(min_level, stdout_level)
      sh = logging.StreamHandler(sys.stdout)
      sh.setFormatter(self.log_formatter())
      log_filter = LogFilter(stdout_level)
      sh.addFilter(log_filter)
      self.log_handlers["stdout"] = sh
      self.addHandler(sh)



    self.remove_handler("file")
    if log_to_file:
      if not os.path.exists(log_dir):
        os.makedirs(log_dir)
      
      log_file_path = f"{log_dir}/process.log"
      file_level = self.get_int_level(file_log.get("level", self.level))
      min_level = min(min_level, file_level)
      self.create_rotating_log("file", log_file_path, **file_log)
      
    self.setLevel(min_level)

  
  def remove_handler(self, handler_name):
    cur_logger = self.log_handlers.get(handler_name)
    if cur_logger:
      self.log_handlers.pop(handler_name)
      self.removeHandler(cur_logger)
  
  def create_rotating_log(self, handler_name, path, **kwargs):
    """
    Creates a rotating log
    """
    keys = ["mode", "maxBytes", "backupCount", "encoding", "delay"]
    default = {"maxBytes": 128_000_000, "backupCount": 10}
    filedict = { akey: kwargs[akey] for akey in keys if kwargs.get(akey) }
    # if filedict.get("maxBytes")
    filedict['maxBytes'] = self.to_i(filedict.get("maxBytes")) or default['maxBytes']
    filedict['backupCount'] = self.to_i(filedict.get("backupCount")) or default['backupCount']
    default.update(**filedict)

    file_level = self.get_int_level(kwargs.get("level", self.level))
    # add a rotating handler
    handler = RotatingFileHandler(path, **default)
    handler.setFormatter(self.log_formatter())
    log_filter = LogFilter(file_level)
    handler.addFilter(log_filter)
    self.log_handlers[handler_name] = handler                                  
    self.addHandler(handler)

  
  def log_formatter(self):
    return DataJsonFormatter('(timestamp) (level) (name) (message)')

  def get_int_level(self, level):
      
      if not isinstance(level, int):
        level = logging.getLevelName(level)
        if not isinstance(level, int):
          level = self.level
      return level

  def to_i(self, val):
    try:
      return int(val)
    except Exception as e:
      return None
    

class LogFilter(logging.Filter):
    """Filters (lets through) all messages with level >= LEVEL"""
    def __init__(self, level):
        self.level = level
    def filter(self, record):
        # "<" instead of "<=": since logger.setLevel is inclusive, this should
        # be exclusive
        return record.levelno >= self.level

setLoggerClass(ServiceProcessLogger)