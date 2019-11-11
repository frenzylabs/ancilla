from .data_handler import DataHandler
import json

class PrinterHandler(DataHandler):
  def __init__(self, device, *args):
      self.device = device

  def handle(self, data):
      if not data or len(data) < 3:
        return

      identifier, status, msg = data
      if type(msg) == bytes:
          msg = msg.decode('utf-8')


      newmsg = msg
      prefix = "echo:"
      if msg.startswith(prefix):
        newmsg = msg[len(prefix):]

      
      cmd = self.device.command_queue.current_command
      if cmd:
        # identifier = identifier + b'.printer.log'
        print(f"INSIDE CMD on data {cmd.command}", flush=True)
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

        payload = {"status": cmdstatus, "sequence": cmd.sequence, "command": cmd.command, "resp": newmsg, "req_id": cmd.request_id}
      else:
        payload = {"status": status.decode('utf-8'), "resp": newmsg}

      
      return [b'events.printer.data_received', identifier, json.dumps(payload).encode('ascii')]
      # super().on_data(data)
      # return data