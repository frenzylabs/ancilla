# from ..node.app import ConfigDict
from ..node.app import App
import json


class ServiceJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        # print(f"Serialize obj = {type(obj).__name__}", flush=True)
        if hasattr(obj, "to_json"):
            res = obj.to_json()
            return self.default(res)
        if type(obj).__name__ == "ConfigDict":
        # if isinstance(obj, ConfigDict):
          return self.default(obj.__dict__)
        # if type(obj).__name__ == "App":
        if isinstance(obj, App):
            # print(f"OBJ {obj.__dict__}")
            # return "node"
            # print(f"self = {self}", flush=True)
            return self.default(obj.config)
            json.dumps(obj.config)
        return obj