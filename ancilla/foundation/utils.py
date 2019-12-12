from .node.app import App, ConfigDict
import json

class Dotdict(dict):
    """dot.notation access to dictionary attributes"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


class ServiceJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, "to_json"):
            res = obj.to_json()
            return self.default(res)
        if isinstance(obj, ConfigDict):
          return self.default(obj.__dict__)
        if isinstance(obj, App):
            # print(f"OBJ {obj.__dict__}")
            # return "node"
            # print(f"self = {self}", flush=True)
            return self.default(obj.config)
            json.dumps(obj.config)
        return obj