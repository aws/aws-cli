# Copyright (c) 2012 Mitch Garnaat http://garnaat.org/
# Copyright 2012 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish, dis-
# tribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the fol-
# lowing conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABIL-
# ITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
# SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
"""
Responsible for finding and loading all JSON data.

This module serves as the abstraction layer over the underlying data
needed by the rest of the UNCLE system.  Currently, this data is in the
form of JSON data files these kinds of details must be hidden from the
rest of the system.

All of the data is presented to the rest of the system in a hierarchical,
filesystem-like, manner.  The basic hierarchy is:

    * provider
      * service
        * operation
          * parameter
            * ...

You can reference this hierarchical data using a path similar to a file
system, e.g. provider/service/operation/parameter/... etc.

The main interface into this module is the ``get_data`` function which
takes a path specificiation as it's only parameter.  This function will
either return the specified data or raise an exception if the data cannot
be found or loaded.
"""
import os
import json
import logging
import botocore.exceptions

logger = logging.getLogger(__name__)

_data_cache = {}
_search_paths = []


def _load_data(session, data_path):
    logger.debug('Attempting to Load: %s' % data_path)
    data = {}
    file_name = data_path + '.json'
    for path in get_search_path(session):
        file_path = os.path.join(path, file_name)
        if os.path.isfile(file_path):
            fp = open(file_path)
            try:
                new_data = json.load(fp)
                fp.close()
                logger.debug('Found data file: %s' % file_path)
                data.update(new_data)
            except:
                logger.error('Unable to load file: %s' % file_path)
    if data:
        _data_cache[data_path] = data
    return data


def _load_nested_data(session, data_path):
    # First we need to prime the pump, so to speak.
    # We need to make sure the parents of the nested reference have
    # been loaded before we attempt to get the nested data.
    mod_names = data_path.split('/')
    for i, md in enumerate(mod_names):
        mod_name = '/'.join(mod_names[0:i + 1])
        d = _load_data(session, mod_name)
    data = None
    prefixes = [dp for dp in _data_cache.keys() if data_path.startswith(dp)]
    if prefixes:
        prefix = max(prefixes)
        data = _data_cache[prefix]
        attrs = [s for s in data_path.split('/') if s not in prefix.split('/')]
        for attr in attrs:
            if isinstance(data, dict):
                if attr in data:
                    data = data[attr]
                else:
                    data = None
                    break
            elif isinstance(data, list):
                for item in data:
                    if 'name' in item and item['name'] == attr:
                        data = item
                        break
    if data is not None:
        _data_cache[data_path] = data
    return data


def get_search_path(session):
    """
    Return the complete data path used when searching for
    data files.

    """
    p = os.path.split(__file__)[0]
    p = os.path.split(p)[0]
    p = _search_paths + [os.path.join(p, 'botocore/data')]
    env_var = session.env_vars['data_path']
    if env_var in os.environ:
        paths = os.environ[env_var].split(':')
        for path in paths:
            path = os.path.expandvars(path)
            path = os.path.expanduser(path)
            p.append(path)
    return p


def get_data(session, data_path):
    """
    Finds, loads and returns the data associated with ``data_path``.
    If the file is found, the JSON data is parsed and returned.  The
    data is then cached so that subsequent requests get the data from
    the cache.

    :type data_path: str
    :param data_path: The path to the desired data, relative to
        the root of the JSON data directory.

    :raises `botocore.exceptions.DataNotFoundError`
    """
    if data_path not in _data_cache:
        data = _load_data(session, data_path)
        if not data:
            data = _load_nested_data(session, data_path)
        if data is None:
            raise botocore.exceptions.DataNotFoundError(data_path=data_path)
    return _data_cache[data_path]


def get_service_data(session, service_name, provider_name='aws'):
    """
    Get full data for a service.  This merges the full service data
    with the metadata stored in the services.json file.
    """
    meta_data = get_data(session,
                         '%s/_services/%s' % (provider_name, service_name))
    service_data = get_data(session,
                            '%s/%s' % (provider_name, service_name))
    # Merge metadata about service
    service_data.update(meta_data)
    return service_data
