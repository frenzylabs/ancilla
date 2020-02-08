

from collections.abc import MutableMapping as DictMixin

class MultiDict(DictMixin):
    """ This dict stores multiple values per key, but behaves exactly like a
        normal dict in that it returns only the newest value for any given key.
        There are special methods available to access the full list of values.
    """

    def __init__(self, *a, **k):
        self.dict = dict((k, [v]) for (k, v) in dict(*a, **k).items())

    def __len__(self):
        return len(self.dict)

    def __iter__(self):
        return iter(self.dict)

    def __contains__(self, key):
        return key in self.dict

    def __delitem__(self, key):
        del self.dict[key]

    def __getitem__(self, key):
        return self.dict[key][-1]

    def __setitem__(self, key, value):
        self.append(key, value)

    def keys(self):
        return self.dict.keys()



    def values(self):
        return (v[-1] for v in self.dict.values())

    def items(self):
        return ((k, v[-1]) for k, v in self.dict.items())

    def allitems(self):
        return ((k, v) for k, vl in self.dict.items() for v in vl)

    iterkeys = keys
    itervalues = values
    iteritems = items
    iterallitems = allitems

    
    def get(self, key, default=None, index=-1, type=None):
        """ Return the most recent value for a key.

            :param default: The default value to be returned if the key is not
                   present or the type conversion fails.
            :param index: An index for the list of available values.
            :param type: If defined, this callable is used to cast the value
                    into a specific type. Exception are suppressed and result in
                    the default value to be returned.
        """
        try:
            val = self.dict[key][index]
            return type(val) if type else val
        except Exception:
            pass
        return default

    def append(self, key, value):
        """ Add a new value to the list of values for this key. """
        self.dict.setdefault(key, []).append(value)

    def replace(self, key, value):
        """ Replace the list of values with a single value. """
        self.dict[key] = [value]

    def getall(self, key):
        """ Return a (possibly empty) list of values for a key. """
        return self.dict.get(key) or []

    #: Aliases for WTForms to mimic other multi-dict APIs (Django)
    getone = get
    getlist = getall
