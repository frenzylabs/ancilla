'''
 config_dict.py
 ancilla

 Created by Kevin Musselman (kevin@frenzylabs.com) on 02/08/20
 Copyright 2019 FrenzyLabs, LLC.
'''

import configparser
import weakref

##
##
##
##

_UNSET = object()

class ConfigDict(dict):
    """ A dict-like configuration storage with additional support for
        namespaces, validators, meta-data, overlays and more.

        This dict-like class is heavily optimized for read access. All read-only
        methods as well as item access should be as fast as the built-in dict.
    """

    __slots__ = ('_parent', '_meta', '_change_listener', '_overlays', '_virtual_keys', '_source', '__weakref__')

    def __init__(self):
        self._parent = None
        self._meta = {}
        self._change_listener = []
        #: Weak references of overlays that need to be kept in sync.
        self._overlays = []
        #: Config that is the source for this overlay.
        self._source = None
        #: Keys of values copied from the source (values we do not own)
        self._virtual_keys = set()

    def load_module(self, path, squash=True):
        """Load values from a Python module.

           Example modue ``config.py``::

                DEBUG = True
                SQLITE = {
                    "db": ":memory:"
                }


           >>> c = ConfigDict()
           >>> c.load_module('config')
           {DEBUG: True, 'SQLITE.DB': 'memory'}
           >>> c.load_module("config", False)
           {'DEBUG': True, 'SQLITE': {'DB': 'memory'}}

           :param squash: If true (default), dictionary values are assumed to
                          represent namespaces (see :meth:`load_dict`).
        """
        config_obj = load(path)
        obj = {key: getattr(config_obj, key) for key in dir(config_obj)
               if key.isupper()}

        if squash:
            self.load_dict(obj)
        else:
            self.update(obj)
        return self

    def load_config(self, filename, **options):
        """ Load values from an ``*.ini`` style config file.

            A configuration file consists of sections, each led by a
            ``[section]`` header, followed by key/value entries separated by
            either ``=`` or ``:``. Section names and keys are case-insensitive.
            Leading and trailing whitespace is removed from keys and values.
            Values can be omitted, in which case the key/value delimiter may
            also be left out. Values can also span multiple lines, as long as
            they are indented deeper than the first line of the value. Commands
            are prefixed by ``#`` or ``;`` and may only appear on their own on
            an otherwise empty line.

            Both section and key names may contain dots (``.``) as namespace
            separators. The actual configuration parameter name is constructed
            by joining section name and key name together and converting to
            lower case.

            The special sections ``bottle`` and ``ROOT`` refer to the root
            namespace and the ``DEFAULT`` section defines default values for all
            other sections.

            With Python 3, extended string interpolation is enabled.

            :param filename: The path of a config file, or a list of paths.
            :param options: All keyword parameters are passed to the underlying
                :class:`python:configparser.ConfigParser` constructor call.

        """
        options.setdefault('allow_no_value', True)
        options.setdefault('interpolation',
                               configparser.ExtendedInterpolation())
        conf = configparser.ConfigParser(**options)
        conf.read(filename)
        for section in conf.sections():
            for key in conf.options(section):
                value = conf.get(section, key)
                if section not in ['bottle', 'ROOT']:
                    key = section + '.' + key
                self[key.lower()] = value
        return self

    def load_dict(self, source, namespace=''):
        """ Load values from a dictionary structure. Nesting can be used to
            represent namespaces.

            >>> c = ConfigDict()
            >>> c.load_dict({'some': {'namespace': {'key': 'value'} } })
            {'some.namespace.key': 'value'}
        """
        for key, value in source.items():
            if isinstance(key, str):
                nskey = (namespace + '.' + key).strip('.')
                if isinstance(value, dict):
                    self.load_dict(value, namespace=nskey)
                else:
                    self[nskey] = value
            else:
                raise TypeError('Key has type %r (not a string)' % type(key))
        return self

    def update(self, *a, **ka):
        """ If the first parameter is a string, all keys are prefixed with this
            namespace. Apart from that it works just as the usual dict.update().

            >>> c = ConfigDict()
            >>> c.update('some.namespace', key='value')
        """
        prefix = ''
        if a and isinstance(a[0], str):
            prefix = a[0].strip('.') + '.'
            a = a[1:]
        for key, value in dict(*a, **ka).items():
            self[prefix + key] = value

    def setdefault(self, key, value):
        if key not in self:
            self[key] = value
        return self[key]

    def __setitem__(self, key, value):
        # print(f"INSIDE SET ITEM {key} {value}", flush=True)
        # print(f"Parent= {self._parent}", flush=True)
        if not isinstance(key, str):
            raise TypeError('Key has type %r (not a string)' % type(key))

        
        self._virtual_keys.discard(key)

        value = self.meta_get(key, 'filter', lambda x: x)(value)
        if key in self and self[key] is value:
            return

        self._on_change(key, value)
        dict.__setitem__(self, key, value)

        for overlay in self._iter_overlays():
            overlay._set_virtual(key, value)

    def __delitem__(self, key):
        if key not in self:
            raise KeyError(key)
        if key in self._virtual_keys:
            raise KeyError("Virtual keys cannot be deleted: %s" % key)

        if self._source and key in self._source:
            # Not virtual, but present in source -> Restore virtual value
            dict.__delitem__(self, key)
            self._set_virtual(key, self._source[key])
        else:  # not virtual, not present in source. This is OUR value
            self._on_change(key, None)
            dict.__delitem__(self, key)
            for overlay in self._iter_overlays():
                overlay._delete_virtual(key)

    def _set_virtual(self, key, value):
        """ Recursively set or update virtual keys. Do nothing if non-virtual
            value is present. """
        if key in self and key not in self._virtual_keys:
            return  # Do nothing for non-virtual keys.

        self._virtual_keys.add(key)
        if key in self and self[key] is not value:
            self._on_change(key, value)
        dict.__setitem__(self, key, value)
        for overlay in self._iter_overlays():
            overlay._set_virtual(key, value)

    def _delete_virtual(self, key):
        """ Recursively delete virtual entry. Do nothing if key is not virtual.
        """
        if key not in self._virtual_keys:
            return  # Do nothing for non-virtual keys.

        if key in self:
            self._on_change(key, None)
        dict.__delitem__(self, key)
        self._virtual_keys.discard(key)
        for overlay in self._iter_overlays():
            overlay._delete_virtual(key)

    def _on_change(self, key, value):
        if self._parent:
            x = self._parent._on_change(key, value)
        for cb in self._change_listener:
            if cb(self, key, value):
                return True
        

    def _add_change_listener(self, func):        
        self._change_listener.append(func)
        return func
    
    def _remove_change_listener(self, func):
        f = next((item for item in self._change_listener if item.func == func), None)
        if f:
            self._change_listener.remove(f)
        return func

    def meta_get(self, key, metafield, default=None):
        """ Return the value of a meta field for a key. """
        return self._meta.get(key, {}).get(metafield, default)

    def meta_set(self, key, metafield, value):
        """ Set the meta field for a key to a new value. """
        self._meta.setdefault(key, {})[metafield] = value

    def meta_list(self, key):
        """ Return an iterable of meta field names defined for a key. """
        return self._meta.get(key, {}).keys()

    def _define(self, key, default=_UNSET, help=_UNSET, validate=_UNSET):
        """ (Unstable) Shortcut for plugins to define own config parameters. """
        if default is not _UNSET:
            self.setdefault(key, default)
        if help is not _UNSET:
            self.meta_set(key, 'help', help)
        if validate is not _UNSET:
            self.meta_set(key, 'validate', validate)

    def _iter_overlays(self):
        for ref in self._overlays:
            overlay = ref()
            if overlay is not None:
                yield overlay

    def _make_overlay(self):
        """ (Unstable) Create a new overlay that acts like a chained map: Values
            missing in the overlay are copied from the source map. Both maps
            share the same meta entries.

            Entries that were copied from the source are called 'virtual'. You
            can not delete virtual keys, but overwrite them, which turns them
            into non-virtual entries. Setting keys on an overlay never affects
            its source, but may affect any number of child overlays.

            Other than collections.ChainMap or most other implementations, this
            approach does not resolve missing keys on demand, but instead
            actively copies all values from the source to the overlay and keeps
            track of virtual and non-virtual keys internally. This removes any
            lookup-overhead. Read-access is as fast as a build-in dict for both
            virtual and non-virtual keys.

            Changes are propagated recursively and depth-first. A failing
            on-change handler in an overlay stops the propagation of virtual
            values and may result in an partly updated tree. Take extra care
            here and make sure that on-change handlers never fail.

            Used by Route.config
        """
        # Cleanup dead references
        self._overlays[:] = [ref for ref in self._overlays if ref() is not None]

        overlay = ConfigDict()
        overlay._meta = self._meta
        overlay._source = self
        self._overlays.append(weakref.ref(overlay))
        for key in self:
            overlay._set_virtual(key, self[key])
        return overlay

    # def __getitem__(self, key):
    #     print(f"GET ITEM {key}", flush=True)
    #     return super().__getitem__(key)

    def __getattr__(self, key):
    #   print(f"INSIDE configdict GEt attr {key}", flush=True)
      res = self.get(key)
      if isinstance(res, ConfigDict):
        print(f"Key {key} is a ConfigDict", flush=True)
        res._parent = self

      return res
    #   return 'hi'
    
    def __setattr__(self, key, value):
    #   print(f"INSIDE configdict SET attr", flush=True)
    #   print(self)
    #   print(f"{key}, {value}")
      if key in self.__slots__:
          return super().__setattr__(key, value)
      else:
        self.__setitem__(key, value)
        #   self.update(key=val)
        #   self[key] = val

    def to_json(self):
        return {k : v for (k, v) in self.items()}



