from .data_handler import DataHandler

class KeyValueHandler(DataHandler):
  def __init__(self, device, *args):
      self.device = device      
      self.current_key 

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
        cmdstatus = None

        if status == b'error':
          cmdstatus = "error"
          self.device.command_queue.finish_command(status="error")
        else:
          if newmsg.startswith("busy:"):
            self.device.command_queue.update_expiry()
          else:
            cmd.response.append(newmsg)

          if newmsg.startswith("ok"):
            cmdstatus = "finished"
            self.device.command_queue.finish_command()

      return [identifier, status, newmsg.encode('ascii')]
