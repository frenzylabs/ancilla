import time
from ...api import Api
from .events import Printer as PrinterEvent
from ....data.models import Print, Printer

import asyncio
class PrinterApi(Api):
  # def __init__(self, service):
  #   super().__init__(service)
  #   self.setup_api()
    

  def setup(self):
    super().setup()
    self.service.route('/hello', 'GET', self.hello)
    self.service.route('/connection', 'POST', self.connect)
    self.service.route('/connection', 'DELETE', self.disconnect)
    self.service.route('/print', 'POST', self.print)
    self.service.route('/prints', 'GET', self.prints)



  async def hello(self, request, *args, **kwargs):
    print("INSIDE HELLO")
    print(self)
    await asyncio.sleep(2)
    print("Hello AFter first sleep", flush=True)
    await asyncio.sleep(5)
    print("Hello AFter 2 sleep", flush=True)
    return "hello"

  def connect(self, *args):
    return self.service.connect()
  
  def disconnect(self, *args):
    if self.service.connector:
        self.service.stop()
    return {"status": "disconnected"}

  def print(self, request, *args):
    return self.service.start_print(request.params)
  
  def prints(self, request, *args):
    print(f"INSIDE PRINTS {self.service.printer}", flush=True)
    # prnts = Print.select().order_by(Print.created_at.desc())
    return {"prints": [p.json for p in self.service.printer.prints.order_by(Print.created_at.desc())]}

  
  # def start_print(self, *args):
  #   try:
  #     res = data.decode('utf-8')
  #     payload = json.loads(res)
  #     # name = payload.get("name") or "PrintTask"
  #     method = payload.get("method")
  #     pt = PrintTask("print", request_id, payload)
  #     self.task_queue.put(pt)
  #     loop = IOLoop().current()
  #     loop.add_callback(partial(self._process_tasks))

  #   except Exception as e:
  #     print(f"Cant Start Print task {str(e)}", flush=True)

  #   return {"queued": "success"}

    

  
# @app.route('/hello/<name>')
# def hello(name):
#   return 'Hello %s' % name

# def state(service, *args):
#   return "State"


