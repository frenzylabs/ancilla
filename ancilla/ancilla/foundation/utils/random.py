'''
 random.py
 ancilla

 Created by Kevin Musselman (kevin@frenzylabs.com) on 02/08/20
 Copyright 2019 FrenzyLabs, LLC.
'''



def fullpath(o):
  module = o.__class__.__module__
  if module is None or module == str.__class__.__module__:
    return o.__class__.__name__  # Avoid reporting __builtin__
  else:
    return module + '.' + o.__class__.__name__


def makelist(data):  # This is just too handy
    if isinstance(data, (tuple, list, set, dict)):
        return list(data)
    elif data:
        return [data]
    else:
        return []

