class EventPack(object):
  def __init__(self, name, sender, data, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.name = name
    self.sender = sender
    self.data = data
  

  def to_json(self):
    return self.__dict__
