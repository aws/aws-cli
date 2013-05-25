#!/usr/bin/env python
# Copyright 2012-2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

import logging
import os
import requests
import six

logger = logging.getLogger(__name__)

def get_file(session, prefix, path):
    s = None
    file_path = path[len(prefix):]
    file_path = os.path.expanduser(file_path)
    file_path = os.path.expandvars(file_path)
    if os.path.isfile(file_path):
        try:
            fp = open(file_path)
            s = fp.read()
            fp.close()
        except:
            msg = 'Unable to load paramfile: %s' % path
            logger.debug(msg)
    return s

def get_uri(session, prefix, uri):
    s = None
    try:
        r = requests.get(uri)
        if r.status_code == 200:
            s = r.text
    except:
        msg = 'Unable to retrieve: %s' % uri
        logger.debug(msg)
    return s

# TODO - Add s3n: support

PrefixMap = {'file://': get_file,
             'http://': get_uri,
             'https://': get_uri}


def get_paramfile(session, path):
    """
    It is possible to pass parameters to operations by referring
    to files or URI's.  If such a reference is detected, this
    function attempts to retrieve the data from the file or URI
    and returns it.  If there are any errors or if the ``path``
    does not appear to refer to a file or URI, a ``None`` is
    returned.
    """
    data = None
    if isinstance(path, six.string_types):
        for prefix in PrefixMap:
            if path.startswith(prefix):
                data = PrefixMap[prefix](session, prefix, path)
    return data
