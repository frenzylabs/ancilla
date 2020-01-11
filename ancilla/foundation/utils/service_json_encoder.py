# from ..node.app import ConfigDict
from ..node.app import App
import json


class ServiceJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        # print(f"Serialize obj = {type(obj).__name__}", flush=True)
        if hasattr(obj, "to_json"):
            # print(f"TO JSON {obj}")
            res = obj.to_json()
            return res
            # return self.default(res)
        elif type(obj).__name__ == "ConfigDict":
        # if isinstance(obj, ConfigDict):
        #   print(f"ConfigDict JSON {obj}")
          return self.default(obj.__dict__)
        # if type(obj).__name__ == "App":
        elif isinstance(obj, App):
            # print(f"OBJ {obj.__dict__}")
            # return "node"
            # print(f"Appself = {self}", flush=True)
            return self.default(obj.config)
            json.dumps(obj.config)
        return json.dumps(obj)
        # return json.JSONEncoder.default(self, obj)
        # return obj