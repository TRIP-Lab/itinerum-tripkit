#!/usr/bin/env python
# Kyle Fitzsimmons, 2018-2019
from datetime import date, datetime
import functools
import importlib
import logging
import os
import platform
import uuid
import time
import types


logger = logging.getLogger('itinerum-tripkit')
RUN_TIME = time.time()


# serialize types not handled by default by JSON library to string
def json_serialize(obj):
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, uuid.UUID):
        return str(obj)
    # extremely hacky way to naively serialize peewee objects
    if 'peewee.' in str(type(obj)):
        return str(obj)

    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def os_is_windows():
    return platform.system() == 'Windows'


class UserNotFoundError(Exception):
    pass


# https://realpython.com/primer-on-python-decorators/#a-few-real-world-examples
def timer(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        value = func(*args, **kwargs)
        end = time.perf_counter()
        logger.info(f"{func.__name__} completed in {end - start:.2f} s.")
        return value

    return wrapper


# return the relative path for a given filename in a temporary directory; create
# the directory if it is not already present
def temp_path(filename):
    temp_dir = './_temp'
    if not os.path.exists(temp_dir):
        os.mkdir(temp_dir)
    return os.path.join(temp_dir, filename)


# compare file creation date to the program initialization time and remove if too old;
# returns true when file does not exist at location by end of function call
def clean_up_old_file(filepath):
    if os.path.exists(filepath):
        creation_time = os.path.getctime(filepath)
        if creation_time < RUN_TIME:
            os.remove(filepath)
            return True
        return False
    return True


# Tensorflow code to lazy `contrib` modules only when first called
class LazyLoader(types.ModuleType):
    '''
    Lazily import a module to avoid pulling in large dependencies.
    '''

    def __init__(self, local_name, parent_module_globals, name):
        self._local_name = local_name
        self._parent_module_globals = parent_module_globals

        super(LazyLoader, self).__init__(name)

    def _load(self):
        # import the target module and insert it into the parent's namespace
        module = importlib.import_module(self.__name__)
        self._parent_module_globals[self._local_name] = module

        # update this object's dict so if someone keeps a reference to LazyLoader, lookups are efficient
        # (__getattr__ is only called on lookups that fail)
        self.__dict__.update(module.__dict__)

        return module

    def __getattr__(self, item):
        module = self._load()
        return getattr(module, item)
    
    def __dir__(self):
        module = self._load()
        return dir(module)
