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
import re
import logging

__version__ = '0.8.0'


class NullHandler(logging.Handler):
    def emit(self, record):
        pass

# Configure default logger to do nothing
log = logging.getLogger('botocore')
log.addHandler(NullHandler())


_first_cap_regex = re.compile('(.)([A-Z][a-z]+)')
_number_cap_regex = re.compile('([a-z])([0-9]+)')
_end_cap_regex = re.compile('([a-z0-9])([A-Z])')

ScalarTypes = ('string', 'integer', 'boolean', 'timestamp', 'float', 'double')


def xform_name(name, sep='_'):
    """
    Convert camel case to a "pythonic" name.
    """
    s1 = _first_cap_regex.sub(r'\1' + sep + r'\2', name)
    s2 = _number_cap_regex.sub(r'\1' + sep + r'\2', s1)
    return _end_cap_regex.sub(r'\1' + sep + r'\2', s2).lower()


class BotoCoreObject(object):

    def __init__(self, **kwargs):
        self.name = ''
        self.py_name = None
        self.cli_name = None
        self.type = None
        self.members = []
        self.documentation = ''
        self.__dict__.update(kwargs)
        if self.py_name is None:
            self.py_name = xform_name(self.name, '_')
        if self.cli_name is None:
            self.cli_name = xform_name(self.name, '-')

    def __repr__(self):
        return '%s:%s' % (self.type, self.name)
