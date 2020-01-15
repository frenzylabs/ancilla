'''
 printer.py
 api

 Created by Wess Cope (me@wess.io) on 09/30/19
 Copyright 2019 Wess Cope
'''

from .base          import BaseHandler
from ...data.models import Camera, CameraRecording
from .node_api import NodeApiHandler
from ...node.response import AncillaResponse

class CameraRecordingResource(NodeApiHandler):
  async def get(self, *args):
    try:
      resp = await self.node(self.environ)
      self.set_resp_headers(resp)
      self.set_status(resp.status_code)
      if self.params.get("video"):
        self.stream_video(resp)
      else:
        self.write(resp.body)

    except AncillaResponse as e:
      print(f"ancillagetexception = {e}", flush=True)  
      self.set_resp_headers(e)   
      self.set_status(e.status_code)
      self.write(e.body)
    except Exception as e:
      print(f"getexception = {e}", flush=True)    
      self.set_status(400)
      self.write({"error": str(e)})

    finally:
      self.finish()

  # def post(self, recordingID):
  #   cr = CameraRecording.get_by_id(recordingID)
    
  #   kind = self.params.get('cameraID', None)
  #   name = self.params.get('name', None)
  #   camera = Camera(**self.params)
    
  #   if not camera.is_valid:
  #     self.write_error(400, errors=camera.errors)

  #   camera.save()
  #   self.finish({"camera": camera.json})
    # self.write(camera.json)

    # self.finish()

  def stream_video(self, resp):
    with open(resp.body.get("data").get("video_path"), "rb") as f:
      try:
        while True:
          _buffer = f.read(4096)
          if _buffer:
            self.write(_buffer)
          else:
            f.close()
            return
      except Exception as e:
        raise e