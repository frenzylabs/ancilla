import time
from .api import Api
from ..events import Event
from ...data.models import Service, Printer, Camera

import asyncio

class LayerkeepApi(Api):

  def setup(self):
    super().setup()
    self.service.route('/gcode_files', 'GET', self.gcodes)
    # self.service.route('/services/testing/<name>', 'GET', self.testname)
    # self.service.route('/test', 'GET', self.test)
    # self.service.route('/smodel/<model_id>', 'GET', self.service_model)
    # self.service.route('/smodel/<model_id>', ['POST', 'PATCH'], self.update_service_model)
    # self.service.route('/services/test', 'GET', self.test)
    # self.service.route('/services/camera', 'GET', self.listCameras)
    # self.service.route('/services/camera', 'POST', self.createCamera)
    # self.service.route('/services/printer', 'POST', self.createPrinter)
    # self.service.route('/services/printer', 'GET', self.listPrinters)
    # self.service.route('/services/<service>/<service_id><other:re:.*>', ['GET', 'PUT', 'POST', 'DELETE', 'PATCH'], self.catchUnmountedServices)  
    # self.service.route('/services/<name><other:re:.*>', 'GET', self.catchIt)

  # _SERVICE_MODELS_ = ['printer', 'camera']
  def gcodes(self, *args):
    allservices = []
    for service in Service.select():
      js = service.json
      model = service.model
      if model:
        js.update(model=model.to_json(recurse=False))
      allservices.append(js)
    
    return {'services': allservices}

    # return {'services': [service.json for service in Service.select()]}

