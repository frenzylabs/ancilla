'''
 data_handler.py
 ancilla

 Created by Kevin Musselman (kevin@frenzylabs.com) on 01/08/20
 Copyright 2019 FrenzyLabs, LLC.
'''

import logging
from logging.handlers import RotatingFileHandler
from pythonjsonlogger import jsonlogger
import os, sys
from datetime import datetime
from ...env import Env


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


class DataHandler(object):

  def __init__(self, service, *args):
    self.service = service
    self.log_handlers = {}
    self.setup_logger()

  def handle(self, data):
    return data

  def model_updated(self):
    self.setup_logger()


  def setup_logger(self):
    log_settings = self.service.model.settings.get("logging", {})
    log_to_stout = log_settings.get("stdout", False)
    save_log     = log_settings.get("save", {})    
    loglevel     = log_settings.get("level", "INFO")
    savelogfile  = save_log.get("on", False)

    logger_name = f"ServiceDataLog{self.service.model.id}"
    self.logger = logging.getLogger(logger_name)
    self.logger.setLevel(loglevel)
    
    if log_to_stout:
      if not self.log_handlers.get("stdout"):
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(self.log_formatter())
        self.log_handlers["stdout"] = sh
        self.logger.addHandler(sh)
    else:
      self.remove_logger("stdout")


    self.remove_logger(logger_name)
    if savelogfile:
      # if not self.log_handlers.get(logger_name):
      log_path = "/".join([Env.ancilla, "services", f"service{self.service.model.id}", "log"])
      if not os.path.exists(log_path):
        os.makedirs(log_path)
      
      log_file_path = f"{log_path}/data.log"
      save_log_settings = save_log.get("settings", {})
      self.create_rotating_log(logger_name, log_file_path, **save_log_settings)

  
  def remove_logger(self, logger_name):
    cur_logger = self.log_handlers.get(logger_name)
    if cur_logger:
      # logger = logging.getLogger(logger_name)
      self.log_handlers.pop(logger_name)
      self.logger.removeHandler(cur_logger)
  
  def create_rotating_log(self, logger_name, path, **kwargs):
    """
    Creates a rotating log
    """
    default = {"maxBytes": 128_000_000, "backupCount": 10}
    default.update(kwargs)

    # add a rotating handler
    handler = RotatingFileHandler(path, **default)
    handler.setFormatter(self.log_formatter())
    self.log_handlers[logger_name] = handler                                  
    self.logger.addHandler(handler)

  
  def log_formatter(self):
    return DataJsonFormatter('(timestamp) (level) (name) (message)')
