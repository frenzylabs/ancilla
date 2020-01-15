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
        print(f"INSIDE CMD on data {cmd.command}", flush=True)
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
      # super().on_data(data)
      # return data


# ', b'start\n']
# Printer ON DATA [b'wessender', b'resp', b'echo:Marlin bugfix-2.0.x\n']
# Printer ON DATA [b'wessender', b'resp', b'\n']
# Printer ON DATA [b'wessender', b'resp', b'echo: Last Updated: 2019-10-31 | Author: (wesscope, Ender5)\n']
# Printer ON DATA [b'wessender', b'resp', b'echo:Compiled: Nov  1 2019\n']
# Printer ON DATA [b'wessender', b'resp', b'echo: Free Memory: 11623  PlannerBufferBytes: 1200\n']
# Printer ON DATA [b'wessender', b'resp', b'echo:SD card ok\n']
# Printer ON DATA [b'wessender', b'resp', b'echo:V70 stored settings retrieved (604 bytes; crc 30214)\n']
# Printer ON DATA [b'wessender', b'resp', b'echo:  G21    ; Units in mm (mm)\n']
# Printer ON DATA [b'wessender', b'resp', b'echo:  M149 C ; Units in Celsius\n']
# Printer ON DATA [b'wessender', b'resp', b'\n']
# Printer ON DATA [b'wessender', b'resp', b'echo:Filament settings: Disabled\n']
# Printer ON DATA [b'wessender', b'resp', b'echo:  M200 D1.75\n']
# Printer ON DATA [b'wessender', b'resp', b'echo:  M200 D0\n']
# Printer ON DATA [b'wessender', b'resp', b'echo:Steps per unit:\n']
# Printer ON DATA [b'wessender', b'resp', b'echo: M92 X80.00 Y80.00 Z400.00 E418.75\n']
# Printer ON DATA [b'wessender', b'resp', b'echo:Maximum feedrates (units/s):\n']
# Printer ON DATA [b'wessender', b'resp', b'echo:  M203 X500.00 Y500.00 Z5.00 E25.00\n']
# Printer ON DATA [b'wessender', b'resp', b'echo:Maximum Acceleration (units/s2):\n']
# Printer ON DATA [b'wessender', b'resp', b'echo:  M201 X500.00 Y500.00 Z100.00 E5000.00\n']
# Printer ON DATA [b'wessender', b'resp', b'echo:Acceleration (units/s2): P<print_accel> R<retract_accel> T<travel_accel>\n']
# Printer ON DATA [b'wessender', b'resp', b'echo:  M204 P500.00 R500.00 T500.00\n']
# Printer ON DATA [b'wessender', b'resp', b'echo:Advanced: B<min_segment_time_us> S<min_feedrate> T<min_travel_feedrate> J<junc_dev>\n']
# Printer ON DATA [b'wessender', b'resp', b'echo:  M205 B20000.00 S0.00 T0.00 J0.08\n']
# Printer ON DATA [b'wessender', b'resp', b'echo:Home offset:\n']
# Printer ON DATA [b'wessender', b'resp', b'echo:  M206 X0.00 Y0.00 Z0.00\n']
# Printer ON DATA [b'wessender', b'resp', b'echo:Auto Bed Leveling:\n']
# Printer ON DATA [b'wessender', b'resp', b'echo:  M420 S0 Z0.00\n']
# Printer ON DATA [b'wessender', b'resp', b'echo:Material heatup parameters:\n']
# Printer ON DATA [b'wessender', b'resp', b'echo:  M145 S0 H185 B45 F255\n']
# Printer ON DATA [b'wessender', b'resp', b'echo:  M145 S1 H240 B0 F255\n']
# Printer ON DATA [b'wessender', b'resp', b'echo:PID settings:\n']
# Printer ON DATA [b'wessender', b'resp', b'echo:  M301 P37.71 I4.30 D82.63\n']
# Printer ON DATA [b'wessender', b'resp', b'echo:Z-Probe Offset (mm):\n']
# Printer ON DATA [b'wessender', b'resp', b'echo:  M851 X-42.00 Y-16.00 Z-1.75\n']
# Printer ON DATA [b'wessender', b'resp', b'echo:SD card ok\n']
# MSG: ["wessender", "periodic", {"name": "temp", "method": "M105\n"}]      