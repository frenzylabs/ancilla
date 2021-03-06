'''
 event_pack.py
 ancilla

 Created by Kevin Musselman (kevin@frenzylabs.com) on 01/08/20
 Copyright 2019 FrenzyLabs, LLC.
'''

class EventPack(object):
  def __init__(self, name, sender, data, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.name = name
    self.sender = sender
    self.data = data
  

  def to_json(self):
    return self.__dict__

  def get(self, key):
    if key == 'data':
      return self.data
    if key == 'name':
      return self.name
    if key == 'sender':
      return self.sender
    return None
