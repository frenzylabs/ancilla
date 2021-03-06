'''
 camera.py
 ancilla

 Created by Kevin Musselman (kevin@frenzylabs.com) on 01/08/20
 Copyright 2019 FrenzyLabs, LLC.
'''

import time
from .api import Api
from ..events.camera import Camera as CameraEvent
from ...data.models import Camera, Service, CameraRecording
from ..response import AncillaError

import asyncio
import os
import re
import math

MB = 1 << 20
BUFF_SIZE = 10 * MB

class CameraApi(Api):

  def setup(self):
    super().setup()
    self.service.route('/video_processor_stream', 'GET', self.get_video_processor)
    self.service.route('/recordings', 'GET', self.recordings)
    self.service.route('/recordings/<recording_id>', 'GET', self.get_recording)
    self.service.route('/recordings/<recording_id>', 'DELETE', self.delete_recording)
    self.service.route('/recordings/<recording_id>/video', 'GET', self.get_video)
    self.service.route('/recordings/<recording_id>/stop', 'POST', self.stop_recording)
    self.service.route('/record', 'POST', self.record)
    self.service.route('/connection', 'POST', self.connect)
    self.service.route('/connection', 'DELETE', self.disconnect)
    self.service.route('/', ['PATCH', 'PUT'], self.update_service)


  async def update_service(self, request, *args):
    # s = self.service.model
    s = Service.get_by_id(self.service.model.id)
    frozen_keys = ['id', 'created_at', 'updated_at', 'service']
    with Service._meta.database.atomic() as transaction:
      try:
        
        newname = request.params.get("name")
        if newname:
          s.service_name = newname
        model = s.model

        if model:
          modelkeys = model.__data__.keys() - frozen_keys
          for k in modelkeys:
            kval = request.params.get(k)
            if kval:
              model.__setattr__(k, kval)
          
          model_settings = request.params.get("model_settings")
          if model_settings:
            model.settings = model_settings

          if not model.is_valid:
            raise AncillaError(400, {"errors": model.errors})

          model.save()

        if request.params.get('configuration') != None:
          s.configuration = request.params.get('configuration')
        if request.params.get('settings') != None:
          s.settings = request.params.get('settings')
        if request.params.get('event_listeners'):
          s.event_listeners = request.params.get('event_listeners')
        s.save()
        smodel = s.json
        smodel.update(model=model.to_json(recurse=False))
        return {"service_model": smodel}
      except Exception as e:
        # Because this block of code is wrapped with "atomic", a
        # new transaction will begin automatically after the call
        # to rollback().
        transaction.rollback()
        # return {"Error"}
        raise e


  def connect(self, *args):
    return self.service.connect()
  
  async def disconnect(self, *args):
    # if self.service.connector:
    await self.service.stop()
    return {"status": "disconnected"}

  async def stop_recording(self, request, recording_id, *args):
    return await self.service.stop_recording({"data": request.params})

  async def record(self, request, *args):
    return await self.service.start_recording({"data": request.params})

  def get_recording(self, request, recording_id, *args):
    rcd = CameraRecording.get_by_id(recording_id)
    return {"data": rcd.json}

  def get_video(self, request, recording_id, *args):
    rcd = CameraRecording.get_by_id(recording_id)
    path = rcd.video_path
    fp = open(path, "rb")
    
    request.response.set_header('Content-Disposition', 'filename=%s' % "output.mp4")
    if request.params.get("download"):
      request.response.set_header('Content-Type', 'application/octet-stream')
      return fp

    request.response.status = 206
    request.response.set_header('Content-Type', 'video/mp4')    
    request.response.set_header('Accept-Ranges', 'bytes')

    return self.stream_video(request, fp)
    

  def recordings(self, request, *args):
    page = int(request.params.get("page") or 1)
    per_page = int(request.params.get("per_page") or 5)
    q = self.service.camera_model.recordings.order_by(CameraRecording.created_at.desc())

    if request.params.get("q[camera_id]"):
      q = q.where(CameraRecording.camera_id == request.params.get("q[camera_id]"))
    if request.params.get("q[name]"):
      q = q.where(CameraRecording.task_name.contains(request.params.get("q[name]")))
    if request.params.get("q[status]"):
      q = q.where(CameraRecording.status == request.params.get("q[status]"))

    print_id = request.params.get("q[print_id]")
    if print_id:
      if print_id == "0":
        q = q.where(CameraRecording.print_id >> None)  
      else:
        q = q.where(CameraRecording.print_id == print_id)
    if request.params.get("status"):
      q = q.where(CameraRecording.status == request.params.get("status"))
    
    cnt = q.count()
    num_pages = math.ceil(cnt / per_page)
    return {"data": [p.to_json(recurse=True) for p in q.paginate(page, per_page)], "meta": {"current_page": page, "last_page": num_pages, "total": cnt}}

  def delete_recording(self, request, recording_id, *args):
    # rcd = CameraRecording.get_by_id(recording_id)
    return self.service.delete_recording({"data": {"id": recording_id}})
      # return {"success": "Deleted"}


  def get_video_processor(self, request, *args):
    # return {"stream": "tcp://127.0.0.1:5557"}
    processor = self.service.get_or_create_video_processor()    
    if not processor:
      raise AncillaError(400, {"errors": "Video Could Not be Processed"})
    else:
      return processor
      # return {"stream": processer.processed_stream}


  def stream_video(self, request, fp):    
    start, end = self.get_range(request)

    requestedrange =  request.headers.get('Range')
    # if requestedrange == None:
    #   print("NO REQUESTED RANGE",flush=True)
    # else:
    file_size = os.path.getsize(fp.name)
    if end is None:
        end = start + BUFF_SIZE - 1
    end = min(end, file_size - 1)
    end = min(end, start + BUFF_SIZE - 1)
    length = end - start + 1
    # resp.body.buffer_size = length

    request.response.set_header(
        'Content-Range', 'bytes {0}-{1}/{2}'.format(
            start, end, file_size,
        ),
    )
    fp.seek(start)
    bytes = fp.read(length)
    return bytes

  def get_range(self, request):
    range = request.headers.get('Range')
    m = None
    if range:
      m = re.match('bytes=(?P<start>\d+)-(?P<end>\d+)?', range)
    if m:
        start = m.group('start')
        end = m.group('end')
        start = int(start)
        if end is not None:
            end = int(end)
        return start, end
    else:
        return 0, None
