import threading
import time
import sys
import os
import zmq
from zmq.eventloop.zmqstream import ZMQStream
import zmq.asyncio
import json

from tornado.ioloop import IOLoop
from zmq.eventloop.ioloop import PeriodicCallback
from ..zhelpers import zpipe
from ...data.models import PrintSlice, CameraRecording
# from .devices import *
from tornado.gen        import sleep
from .ancilla_task import AncillaTask

from ...utils import Dotdict
from ...env import Env
from ..events.camera import Camera

import datetime
import pickle
import cv2
import numpy as np



class CameraRecordTask(AncillaTask):
  def __init__(self, name, service, payload, *args):
    super().__init__(name, *args)
    # self.request_id = request_id
    self.payload = payload
    self.task_settings = self.payload.get("settings") or {}
    self.service = service
    # self.state = Dotdict({"status": "pending", "model": {}})
    self.state.update({"name": name, "status": "pending", "model": {}})
    
    self.root_path = "/".join([Env.ancilla, "services", service.name, "recordings", self.name])
    if not os.path.exists(self.root_path):
      os.makedirs(self.root_path)
    self.image_path = self.root_path + "/images"
    if not os.path.exists(self.image_path):
      os.makedirs(self.image_path)
    self.video_path = self.root_path + "/videos"
    if not os.path.exists(self.video_path):
      os.makedirs(self.video_path)
    
    
    self.recording = CameraRecording(task_name=name, image_path=self.image_path, video_path=self.video_path, settings=self.task_settings, status="pending", camera_snapshot=self.service.camera_model.to_json())
    self.recording.camera = self.service.camera_model

    printmodel = self.payload.get("model")
    if printmodel:
      if printmodel.get("id"):
        self.recording.print_id = printmodel.get("id")

    self.recording.save(force_insert=True) 
    # self.name = self.recording.id

    print(f"CR root path = {self.root_path}")

    self.event_socket = self.service.ctx.socket(zmq.SUB)
    self.event_socket.connect("ipc://publisher")
    self.event_socket.setsockopt(zmq.SUBSCRIBE, self.service.identity + b'.events.camera.data_received')
    self.event_socket.setsockopt(zmq.SUBSCRIBE, self.service.identity + b'.events.camera.connection.closed')
    self.event_stream = ZMQStream(self.event_socket)
    # self.event_stream.linger = 0
    self.event_stream.on_recv(self.on_data)

    self.current_frame_num = 0
    self.current_frame = None
    self.retry = 5
    # ["wessender", "start_print", {"name": "printit", "file_id": 1}]

  # return [b'events.camera.data_received', identifier, frm_num, frame]
  def on_data(self, data):
    # identity, identifier, frm_num, frame = data
    if len(data) == 4:
      topic, service, framenum, imgdata = data
    # print("CR Task, ON DATA", flush=True)
      self.current_frame = imgdata
    else:
      if data[0].endswith(b'connection.closed'):
        self.state.status = "finished"
        self.state.reason = "Connection Disconnected"
    # fnum = int(framenum.decode('utf-8'))

    # imgname = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    # print("fRAME = ", fnum)
    
    # frame = pickle.loads(imgdata)
    # frame = cv2.flip(frame, 1)

    # x = cv2.resize(frame, dsize=(640, 480), interpolation=cv2.INTER_CUBIC)
    # # print(x.shape)

    # x = x.astype(np.uint8)
    # (flag, encodedImage) = cv2.imencode(".jpg", x)

    # self.write(b'--frame\r\n')
    # self.write(b'Content-Type: image/jpeg\r\n\r\n')
    # self.write(encodedImage.tobytes())
    # self.write(b'\r\n\r\n')
    # if self.ready:
    #   IOLoop.current().add_callback(self.flushit)
      
  def flush_camera_frame(self):
    try:
      if not self.current_frame:
        print("NO FRAME TO FLUSH", flush=True)
        return
      imgname = f'{datetime.datetime.now().strftime("%Y%m%d%H%M%S")}-{self.current_frame_num:06}.jpg'
      frame = pickle.loads(self.current_frame)
      frame = cv2.flip(frame, 1)

      x = cv2.resize(frame, dsize=self.video_size, interpolation=cv2.INTER_CUBIC)
      # print(x.shape)

      # x = x.astype(np.uint8)
      # (flag, encodedImage) = cv2.imencode(".jpg", x)
  
      cv2.imwrite(self.image_path+"/"+imgname, x)
      if self.video_writer:
        self.video_writer.write(x)
      self.current_frame_num += 1
      self.current_frame = None
    except Exception as e:
      print(f"ERror saving camera frame {str(e)}", flush=True)
      if self.retry > 0:
        self.retry -= 1
      else:
        self.state.status = "failed"
        self.state.reason = str(e)
        self.state.recording = False
        
        
    # frame_width = int(video.get(3))
    # frame_height = int(video.get(4))
    # videosize = (frame_width,frame_height)
    # videosize = (640,480)
    # videosize = (1028,720)
    # # out = cv2.VideoWriter('output.avi',cv2.VideoWriter_fourcc('M','J','P','G'), 29, videosize)
    # out = cv2.VideoWriter('output.mov',cv2.VideoWriter_fourcc('m','p','4','v'), 29, videosize)

    # i = 120
    # while i > 0:
    #   i = i - 1
    #   ret, frame = video.read()
    #   if ret == True: 
    #     x = cv2.resize(frame, dsize=videosize, interpolation=cv2.INTER_CUBIC)
    #     out.write(x)




    # img_array = []
    # fps = 15
    # capSize = (1028,720) # this is the size of my source video
    # fourcc = cv2.cv.CV_FOURCC('m', 'p', '4', 'v') # note the lower case
    # self.vout = cv2.VideoWriter()
    # success = self.vout.open('output.mov',fourcc,fps,capSize,True) 

    # for filename in glob.glob('C:/New folder/Images/*.jpg'):
    #     img = cv2.imread(filename)
    #     height, width, layers = img.shape
    #     size = (width,height)
    #     img_array.append(img)
    
    #     out = cv2.VideoWriter('output.mpeg', self.fourcc, 24.0, (640,480))
    #     out = cv2.VideoWriter('output.avi', cv2.VideoWriter_fourcc(*'MP42'), 15.0, (640,480))
    # out = cv2.VideoWriter('output3.mov',cv2.VideoWriter_fourcc('m','p','4','v'), 29, videosize)    
    # # for filename in glob.glob('images/*.jpg')
    # for filename in sorted(glob.glob(f'images/*.jpg'), key=numericalSort):
    #   img = cv2.imread(filename)
    #   out.write(img)
      
    #   height, width, layers = img.shape
    #   size = (width,height)
    #   img_array.append(img)

    #   img = cv2.imread(filename)
    #       out.write(img)

    # for i in range(len(img_array)):
    #     out.write(img_array[i])

    #     out.release()
          # cv2.waitKey(1)



  async def run(self, dv):
     
    print("STARTING RECORDING", flush=True)
    # request = DeviceRequest.get_by_id(self.request_id)
    # self.device = device
    try:
      # print(f"CONTENT = {content}", flush=True)
      self.timelapse = int(self.task_settings.get("timelapse") or 2) * 1000
      self.settings = self.task_settings.get("settings") or {"size": [640, 480]}
      width, height = self.settings.get("size") or [640, 480]
      self.video_size = (width, height)
      self.video_settings = self.task_settings.get("videoSettings") or {"format": "mp4v"}
      self.video_format = self.video_settings.get("format") or "mp4v"      
      self.video_fps = int(self.video_settings.get("fps") or 10)
      # print(f"self.video_Fps {self.video_fps}  vsize: {self.video_size}, vformat: {self.video_format}", flush=True)
      self.video_writer = cv2.VideoWriter(self.video_path + "/output.mp4", cv2.VideoWriter_fourcc(*self.video_format), self.video_fps, self.video_size)
      # # out = cv2.VideoWriter('output.avi',cv2.VideoWriter_fourcc('M','J','P','G'), 29, videosize)
      # out = cv2.VideoWriter('output.mov',cv2.VideoWriter_fourcc('m','p','4','v'), 29, videosize)
      # name = self.payload.get("name") or ""
      # sf = SliceFile.get(fid)
      
      

      self.service.state.recording = True
      self.service.fire_event(Camera.state.changed, self.service.state)

      self.state.status = "recording"
      self.recording.status = self.state.status
      self.recording.save()
      self.state.model = self.recording
      self.state.id = self.recording.id
      
      self.service.fire_event(Camera.recording.started, self.state)
      self.flush_callback = PeriodicCallback(self.flush_camera_frame, self.timelapse)
      self.flush_callback.start()
      # num_commands = file_len(sf.path)
    except Exception as e:
      print(f"Cant record from camera {str(e)}", flush=True)
      self.state.status = "failed"
      self.state.reason = f"Cant record from camera {str(e)}"
      self.service.fire_event(Camera.recording.failed, {"status": "failed", "reason": str(e)})
      # return {"status": "failed"}

    # self.state.status = "running"
    while self.state.status == "recording":
      await sleep(0.1)


    print("FINSIHED RECORDING", flush=True)

    self.recording.status = "finished"
    self.recording.reason = self.state.reason or ""
    self.recording.save()
    self.service.fire_event(Camera.recording.state.changed, self.state)
    self.service.state.recording = False    
    self.flush_callback.stop()
    self.event_stream.close()
    if self.video_writer:
      self.video_writer.release()
    return {"state": self.state}

  def cancel(self):
    self.state.status = "cancelled"
  
  def finished(self):
    self.state.status = "finished"
    # self.device.add_command(request_id, 0, 'M0\n', True, True)

  def pause(self):
    self.flush_callback.stop()
  
  def resume(self):
    self.flush_callback.start()
    # self.state.status = "paused"

  def get_state(self):
    print("get state", flush=True)
    self.state.model = self.service.current_print.json
    self.service.fire_event(Camera.recording.state.changed, self.state)
    
    # self.publish_request(request)
  
