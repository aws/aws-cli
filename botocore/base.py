# Copyright (c) 2012-2013 Mitch Garnaat http://garnaat.org/
# Copyright 2012-2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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


Examples
========

Get the service description for ec2::

    data = get_data('aws/ec2')

Get the operations for ec2::

    data = get_data('aws/ec2/operations')

Get a specific operation::

    data = get_data('aws/ec2/operations/DescribeInstances')

Get the member args for an operations::

    data = get_data('aws/ec2/operations/DescribeInstances/input/members')

"""
import os
import glob
import logging

from botocore.compat import OrderedDict, json
import botocore.exceptions

logger = logging.getLogger(__name__)

_data_cache = {}
_search_paths = []


def _load_data(session, data_path):
    logger.debug('Attempting to load: %s', data_path)
    data = {}
    file_name = data_path + '.json'
    for path in get_search_path(session):
        file_path = os.path.join(path, file_name)
        dir_path = os.path.join(path, data_path)
        # Is the path a directory?
        if os.path.isdir(dir_path):
            logger.debug('Found data dir: %s', dir_path)
            try:
                data = []
                for pn in sorted(glob.glob(os.path.join(dir_path, '*.json'))):
                    fn = os.path.split(pn)[1]
                    fn = os.path.splitext(fn)[0]
                    if not fn.startswith('_'):
                        data.append(fn)
            except:
                logger.error('Unable to load dir: %s', dir_path,
                             exc_info=True)
            break
        elif os.path.isfile(file_path):
            fp = open(file_path)
            try:
                new_data = json.load(fp, object_pairs_hook=OrderedDict)
                fp.close()
                logger.debug('Found data file: %s', file_path)
                if data is not None:
                    data.update(new_data)
                else:
                    data = new_data
                break
            except:
                logger.error('Unable to load file: %s', file_path,
                             exc_info=True)
        else:
            logger.error('Unable to find file: %s', file_path)
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
        _load_data(session, mod_name)
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
        # If we have gotten here and the data is still the original
        # prefix data, it means we did not find the sub data.
        if data == _data_cache[prefix]:
            data = None
    if data is not None:
        _data_cache[data_path] = data
    return data


def get_search_path(session):
    """
    Return the complete data path used when searching for
    data files.

    """
    # Automatically add ./botocore/data to the
    # data search path.
    builtin_path = os.path.join(
        os.path.dirname(
            os.path.dirname(
                os.path.abspath(__file__))), 'botocore', 'data')
    paths = [builtin_path]
    search_path = session.get_variable('data_path')
    if search_path is not None:
        extra_paths = search_path.split(os.pathsep)
        for path in extra_paths:
            path = os.path.expandvars(path)
            path = os.path.expanduser(path)
            paths.append(path)
    return paths


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
