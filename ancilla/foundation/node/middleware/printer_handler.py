from .data_handler import DataHandler
from ..events.printer import Printer
import json

class PrinterHandler(DataHandler):
  def __init__(self, device, *args):
      self.device = device

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
        self.device.state.connected = False
        self.device.fire_event(Printer.connection.closed, self.device.state)


      # newmsg = msg
      prefix = "echo:"
      if decodedmsg.startswith(prefix):
        newmsg = decodedmsg[len(prefix):]
      else:
        newmsg = decodedmsg

      
      cmd = self.device.command_queue.current_command
      
      if cmd:        
        # identifier = identifier + b'.printer.log'
        # print(f"INSIDE CMD on data {cmd.command}", flush=True)
        cmdstatus = None


        if status == b'error':
          cmdstatus = "error"
          self.device.command_queue.finish_command(status="error")
        else:
          if newmsg.startswith("busy:"):
            cmdstatus = "busy"
            self.device.command_queue.update_expiry()
          elif newmsg.startswith("Error:"):
            cmdstatus = "error"
            self.device.command_queue.finish_command(status="error")
          else:
            cmdstatus = "running"
            cmd.response.append(newmsg)

          if newmsg.startswith("ok"):
            cmdstatus = "finished"
            self.device.command_queue.finish_command()

        payload = {"status": cmdstatus, "sequence": cmd.sequence, "command": cmd.command, "resp": newmsg, "req_id": cmd.parent_id}
        cmd = None
      else:
        payload = {"status": status.decode('utf-8'), "resp": newmsg}

      
      return [b'events.printer.'+ eventkind, identifier, json.dumps(payload).encode('ascii')]
      # super().on_data(data)
      # return data