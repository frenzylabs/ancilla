import threading
import time
import zmq
import os

import json
from tornado.ioloop import IOLoop

from ..zhelpers import zpipe, socket_set_hwm
from ...data.models import Printer as PrinterModel
from ..device import Device
from .serial_connector import SerialConnector
from ...env import Env
from ...data.models import DeviceRequest
# from queue import Queue
import asyncio
from functools import partial
from tornado.queues     import Queue
from tornado import gen
from tornado.gen        import coroutine, sleep

class Printer(Device):
    connector = None
    endpoint = None         # Server identity/endpoint
    identity = None
    alive = True            # 1 if known to be alive
    ping_at = 0             # Next ping at this time
    expires = 0             # Expires at this time
    workers = []
    state = "IDLE"
    print_queued = False
    task_queue = Queue()

    def __init__(self, ctx, name, **kwargs):
        query = PrinterModel.select().where(PrinterModel.name == name).limit(1)
        self.record = query[0].json
        self.port = self.record['port']
        self.baud_rate = self.record['baud_rate']

        super().__init__(ctx, name, **kwargs)

        # for pr in query:
        #   print(pr.json)
        # print(type(query))
        # print(self.record)
        # self.endpoint = endpoint
        # if identity == None: 
        #   identity = endpoint
        # self.identity = name
        # self.baudrate = baudrate
                
        # self.ping_at = time.time() + 1e-3*PING_INTERVAL
        # self.expires = time.time() + 1e-3*SERVER_TTL

        # self.ctx = zmq.Context()


    # def start(self):
    #   self.pipe, peer = zpipe(self.ctx)
    #   self.alive = True
    #   self.agent = threading.Thread(target=self.run_server, args=(self.ctx,peer,))
    #   self.agent.daemon = True
    #   self.agent.start()
        # ctx = zmq.Context()
        # self.snapshot = ctx.socket(zmq.DEALER)
        # self.snapshot.linger = 0
        # self.snapshot.connect("%s:%i" % (address.decode(),port))
        # self.publisher = ctx.socket(zmq.PUB)
        # # self.subscriber.setsockopt(zmq.SUBSCRIBE, subtree)
        # self.publisher.connect("inproc://publisher")
        # self.conn = SerialConnection(endpoint, baudrate)
        # self.conn.run(reader=self.printerReader)

    def stop(self):
      self.agent.stop()

    def on_message(self, msg):
      print("ON MESSAge", msg)  
      identifier, request_id, cmd, *data = msg
      # if self.connector:
      #   if cmd == "CLOSE":
      #     self.connector.close()
      #   elif cmd == "STATE":
      #     self.connector.close()
      #   else:
      #     self.connector.write(data+b'\n')

      self.input_stream.send_multipart([identifier, request_id, b'Cmd written'])

    def on_data(self, data):
      print("ON DATA", data)
    
    def start(self, *args):
      print("START Printer", flush=True)
      # publisher = ctx.socket(zmq.PUSH)
      # publisher.connect(f"inproc://{self.identity}_collector")
      # publisher.send_multipart([b'ender3', b'hello there'])
      self.connector = SerialConnector(self.ctx, self.identity, self.port, self.baud_rate)
      self.connector.start()
      # serial_conn = SerialConnector(self.identity, "ipc://collector", self.endpoint.decode("utf-8"), self.baudrate, pipe)
      # while self.alive:
      #   try:
      #       cmd, data = pipe.recv_multipart()
      #       print("Received Data: ", data)
      #       # if data:
      #       #   serial_conn.serial.write(data+b'\n')
      #   except Exception as msg:
      #       print('{}'.format(msg))            
      #       # probably got disconnected
      #       break


    def send(self, msg):
      print(msg)
      request_id, action, *lparts = msg
      
      data = b''
      if len(lparts) > 0:
        data = lparts[0]
      
      try:
        request_id = request_id.decode('utf-8')
        action_name = action.decode('utf-8').lower()
        method = getattr(self, action_name)
        if not method:
          return json.dumps({request_id: {'error': f'no action {action} found'}})
        
        res = method(request_id, data)
        return json.dumps({request_id: res})

        # if len(params) > 0:
        #   await method(**params)
        # else:
        #   await method()
      except Exception as e:
        return json.dumps({request_id: {"error": str(e)}})

      # if self.connector:
      #   if cmd == b"CLOSE":
      #     self.connector.close()
      #   elif cmd == b"STATE":
      #     state = {"open": self.connector.serial.is_open}
      #     return json.dumps(state)
      #   else:
      #     self.connector.write(data+b'\n')
      # self.pipe.send_multipart([b"COMMAND", msg])

    def state(self, *args):
      return {"open": self.connector.serial.is_open}

    def pause(self, *args):
      if self.state == "printing":
        self.state = "paused"
      return {"state": self.state}
      

    def command(self, request_id, data):
      # self.input_stream.send_multipart([])
      self.connector.write(data+b'\n')
      request = DeviceRequest.get_by_id(request_id)
      request.state = "Sent"
      request.save()
      return {"sent": "success"}


    def file_len(fname):
      i = 0
      with open(fname) as f:
          for i, l in enumerate(f):
              pass
      return i + 1

    # @asyncio.coroutine
    async def _process_tasks(self):
      # while True:
        print("About to get queue", flush=True)
        async for item in self.task_queue:
          print('consuming {}...'.format(item))
          (method, request_id, msg) = item
          # await self.printer_task(item)
          await method(request_id, msg)
          print("INSIDE PROCESS TASK")

        # todo: do something more useful than sleeping :)
        # yield from asyncio.sleep(random.random())
        # self.task_queue.task_done()

      # async for (method, request_id, msg) in self.task_queue:
      #   # self.write_message({"response" : msg.decode("utf-8")})
      #   await method(request_id, msg)
        # await sleep(0.01)

    async def _add_task(self, msg):
      await self.task_queue.put(msg)

    def printit(self, request_id, data):
      request = DeviceRequest.get_by_id(request_id)
      if self.print_queued:
        request.state = "unschedulable"
        request.save()
        return {"error": "Printer Busy"}
      
      loop = IOLoop().current()
      
      # loop.add_callback()

      # loop.add_callback(partial(self._add_task, (self.printer_task, request_id, data)))
      # if self.task_queue.empty():
      # loop.create_task(self.open())
        # await self._add_task((request_id, data))          
        
      # self.task_queue.put(request_id)
      # await sleep(0.01)
      print("ADDED TO QUEUE")
      self.task_queue.put((self.printer_task, request_id, data))
      loop.add_callback(partial(self._process_tasks))
      self.task_queue.join()
      # else:
      #   self.task_queue.put((self.printer_task, request_id, data))

      return {"queued": "success"}
        
      
      
      # request.payload

    
    # @asyncio.coroutine
    # def run_sink(context):
    #     # Socket to receive messages on
    #     receiver = context.socket(zmq.PULL)
    #     receiver.bind("tcp://*:5558")
    #     # Wait for start of batch
    #     yield from receiver.recv()
    #     # Start our clock now
    #     tstart = time.time()
    #     # Process 100 confirmations
    #     for task_nbr in range(100):
    #         yield from receiver.recv()
    #         if task_nbr % 10 == 0:
    #             sys.stdout.write(':')
    #         else:
    #             sys.stdout.write('.')
    #         sys.stdout.flush()
    #     # Calculate and report duration of batch
    #     tend = time.time()
    #     print("Total elapsed time: %d msec" % ((tend - tstart) * 1000))


    # @asyncio.coroutine
    # def run(loop):
    #     context = Context()
    #     yield from run_sink(context)
        
    # @asyncio.coroutine
    async def printer_task(self, request_id, msg):
        request = DeviceRequest.get_by_id(request_id)
        router = self.ctx.socket(zmq.ROUTER)
        
        # router.setsockopt_string(zmq.ROUTER, u'')
        # router.setsockopt_string(zmq.IDENTITY, f'Task_{request_id}')
        encoded_request_id = request_id.encode('ascii')
        router.identity = encoded_request_id
        print("INSIDE PRINTER TASK = ", request_id)
        socket_set_hwm(router, 1)
        
        # router.identity = f'Task_{request_id}'.encode('ascii')
        # f"ipc://{self.identity}_taskrouter"
        # connect_to = f"ipc://{self.identity.decode('utf-8')}_taskrouter"
        connect_to = f"tcp://127.0.0.1:5558"
        print("connectto = ", connect_to)
        router.connect(connect_to)
        self.state = "printing"
        # credit = PIPELINE   # Up to PIPELINE chunks in transit
        # total = 0           # Total bytes received
        # chunks = 0          # Total chunks received
        # offset = 0          # Offset of next chunk request
        with open(f'{Env.ancilla}/gcodes/test.gcode', "r") as fp:
          cnt = 0
          fp.seek(0, os.SEEK_END)
          endfp = fp.tell()
          print("End File POS: ", endfp)
          fp.seek(0)
          while self.state == "printing":
            # for line in fp:
            line = fp.readline()
            pos = fp.tell()
            # print("File POS: ", pos)
            if pos == endfp:
              break
            
            print("Line {}, POS: {} : {}".format(cnt, pos, line))    
            # router.send_multipart([b"printer", request_id.encode('ascii'), b'command', line.encode('ascii')])
            self.connector.write(line.encode('ascii'))
            # print()
            await sleep(0.1)
            try:
                
                # res = await router.recv_multipart()
                
                cnt += 1
                # print("Response {}".format(res))
                
            except zmq.ZMQError as e:
                print("ERROER", str(e))
                if e.errno == zmq.ETERM:
                    return   # shutting down, quit
                else:
                    raise

        # res = router.recv_multipart()
        # print("RES = ", res)
        # router = ctx.socket(zmq.ROUTER)
        # socket_set_hwm(router, PIPELINE)
        # router.bind("tcp://*:6000")
        # count = 0
        # total = 0
        # while True:

        # while True:
        #     while credit:
        #         # ask for next chunk
        #         yield from dealer.send_multipart([
        #             b"fetch",
        #             b"%i" % total,
        #             b"%i" % CHUNK_SIZE,
        #         ])
        #         offset += CHUNK_SIZE
        #         credit -= 1
        #     try:
        #         chunk = yield from dealer.recv()
        #     except zmq.ZMQError as e:
        #         if e.errno == zmq.ETERM:
        #             return   # shutting down, quit
        #         else:
        #             raise
        #     chunks += 1
        #     credit += 1
        #     size = len(chunk)
        #     total += size
        #     if size < CHUNK_SIZE:
        #         break   # Last chunk received; exit
        # yield from dealer.send_multipart([
        #     b"finish",
        #     b"-1",
        #     b"-1",
        # ])
        # message = "client received %i chunks, %i bytes" % (chunks, total)
        # print(message)
        # print('(client) finished')
        # yield from pipe.send(b"OK")
        # return ('client', message)
      

    # def ping(self, socket):
    #     if time.time() > self.ping_at:
    #         print("SEND PING FOR %s", self.identity)
    #         socket.send_multipart([self.identity, b'PING', b'/'])
    #         self.ping_at = time.time() + 1e-3*PING_INTERVAL
    #     else:
    #       print("NO PING: %s  ,  %s ", time.time(), self.ping_at)

    # def tickless(self, tickless):
    #     if tickless > self.ping_at:
    #         tickless = self.ping_at
    #     return tickless