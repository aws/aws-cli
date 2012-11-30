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
import re
import platform
import logging

__version__ = '0.1.0'
_user_agent_name = 'Boto'


def set_user_agent_name(name):
    global _user_agent_name
    _user_agent_name = name


def user_agent():
    return '%s/%s Python/%s %s/%s' % (_user_agent_name,
                                      __version__,
                                      platform.python_version(),
                                      platform.system(),
                                      platform.release())


class NullHandler(logging.Handler):
    def emit(self, record):
        pass

# Configure default logger to do nothing
log = logging.getLogger(__name__)
log.addHandler(NullHandler())
fmt_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'


def set_debug_logger():
    """
    Convenience function to quickly configure full debug output
    to go to the console.
    """
    log.setLevel(logging.DEBUG)

    # create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    # create formatter
    formatter = logging.Formatter(fmt_string)

    # add formatter to ch
    ch.setFormatter(formatter)

    # add ch to logger
    log.addHandler(ch)


def set_file_logger(log_level, path):
    """
    Convenience function to quickly configure any level of logging
    to a file.

    :type log_level: int
    :param log_level: A log level as specified in the `logging` module

    :type path: string
    :param path: Path to the log file.  The file will be created
        if it doesn't already exist.
    """
    log.setLevel(log_level)

    # create console handler and set level to debug
    ch = logging.FileHandler(path)
    ch.setLevel(log_level)

    # create formatter
    fmt_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(fmt_string)

    # add formatter to ch
    ch.setFormatter(formatter)

    # add ch to logger
    log.addHandler(ch)


_first_cap_regex = re.compile('(.)([A-Z][a-z]+)')
_number_cap_regex = re.compile('([a-z])([0-9]+)')
_end_cap_regex = re.compile('([a-z0-9])([A-Z])')

ScalarTypes = ('string', 'integer', 'boolean', 'timestamp', 'float')


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
        self.type = None
        self.members = []
        self.documentation = ''
        self.__dict__.update(kwargs)
        self.py_name = xform_name(self.name, '_')
        self.cli_name = xform_name(self.name, '-')

    def __repr__(self):
        return '%s:%s' % (self.type, self.name)
