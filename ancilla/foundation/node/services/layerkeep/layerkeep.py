
# from ...events.printer import Printer as PrinterEvent
from ...base_service import BaseService
from ...api.layerkeep import LayerkeepApi


class Layerkeep(BaseService):    
    
    __actions__ = [
        "sync_file"
      ]

    # events = PrinterEvents
    def __init__(self, model, **kwargs):
        super().__init__(model, **kwargs)
        

        # self.printer = PrinterModel.get(PrinterModel.service == model)
        # self.printer = model #query[0]
        
        self.api = LayerkeepApi(self)
        # self.event_class = PrinterEvent
        # self.state = Dotdict({
        #   "status": "Idle",
        #   "connected": False, 
        #   "alive": False,
        #   "printing": False
        # })
        # print(f"Printerevent {PrinterEvent.settings_changed.value()}", flush=True)
        
        # self.state.load_dict({
        #   "status": "Idle",
        #   "connected": False, 
        #   "alive": False,
        #   "printing": False
        # })
        
        print(f"INSIDE Layerkeep INIT = {self.identity}", flush=True)
        # self.register_data_handlers(PrinterHandler(self))


    # @property
    # def actions(self):
    #   return [
    #     "get_state",
    #     "command"
    #   ]

    def test_hook(self, *args):
      print(f"LK TESTHOOK Fired: {args}", flush=True)
