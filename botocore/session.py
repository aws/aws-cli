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

import os
import logging
import platform
import botocore.config
import botocore.credentials
import botocore.base
import botocore.service
from . import __version__


class Session(object):
    """
    The Session object collects together useful functionality
    from `botocore` as well as important data such as configuration
    information and credentials into a single, easy-to-use object.

    :ivar user_agent_name: The name used when constructing the User-Agent
        header when making HTTP requests.
    :ivar user_agent_version: The version used when constructing the
        User-Agent header when making HTTP requests.
    """

    FmtString = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    def __init__(self):
        self.user_agent_name = 'Boto'
        self.user_agent_version = __version__
        self._profile = 'default'
        self._config = None
        self._credentials = None

    @property
    def available_profiles(self):
        return self.get_config().keys()

    @property
    def profile(self):
        return self._profile

    @profile.setter
    def profile(self, profile):
        if profile != self._profile:
            self._credentials = None
        self._profile = profile

    def get_config(self):
        """
        Returns the configuration associated with this session.  If
        the configuration has not yet been loaded, it will be loaded
        using the current `profile` attribute value.  If it has already been
        loaded, the cached configuration will be returned.

        :raises: ConfigNotFound, ConfigParseError
        """
        if self._config is None:
            self._config = botocore.config.get_config()
        return self._config.get(self._profile, None)

    def get_credentials(self, metadata=None):
        """
        Return the :class:`botocore.credential.Credential` object
        associated with this session.  If the credentials have not
        yet been loaded, this will attempt to load them.  If they
        have already been loaded, this will return the cached
        credentials.

        :type metadata: dict
        :param metadata: This parameter allows you to pass in
            EC2 instance metadata containing IAM Role credentials.
            This metadata will be used rather than retrieving the
            metadata from the metadata service.  This is mainly used
            for unit testing.
        """
        if self._credentials is None:
            cfg = self.get_config()
            self._credentials = botocore.credentials.get_credentials(cfg,
                                                                     metadata)
        return self._credentials

    def user_agent(self):
        """
        Return a string suitable for use as a User-Agent header.
        The string will be of the form:

        <agent_name>/<agent_version> Python/<py_ver> <plat_name>/<plat_ver>

        Where:

         - agent_name is the value of the `user_agent_name` attribute
           of the session object (`Boto` by default).
         - agent_version is the value of the `user_agent_version`
           attribute of the session object (the botocore version by default).
           by default.
         - py_ver is the version of the Python interpreter beng used.
         - plat_name is the name of the platform (e.g. Darwin)
         - plat_ver is the version of the platform

        """
        return '%s/%s Python/%s %s/%s' % (self.user_agent_name,
                                          self.user_agent_version,
                                          platform.python_version(),
                                          platform.system(),
                                          platform.release())

    def add_search_path(self, search_paths):
        for path in search_paths:
            botocore.base.add_search_path(path)

    def get_data(self, data_path):
        """
        Retrieve the data associated with `data_path`.

        :type data_path: str
        :param data_path: The path to the data you wish to retrieve.
        """
        return botocore.base.get_data(data_path)

    def get_service(self, service_name, provider_name='aws'):
        """
        Get information about a service.

        :type service_name: str
        :param service_name: The name of the service (e.g. 'ec2')

        :type provider_name: str
        :param provider_name: The name of the provider.  Defaults
            to 'aws'.

        :returns: :class:`botocore.service.Service`
        """
        return botocore.service.get_service(self, service_name, provider_name)

    def set_debug_logger(self):
        """
        Convenience function to quickly configure full debug output
        to go to the console.
        """
        log = logging.getLogger('botocore')
        log.setLevel(logging.DEBUG)

        # create console handler and set level to debug
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)

        # create formatter
        formatter = logging.Formatter(self.FmtString)

        # add formatter to ch
        ch.setFormatter(formatter)

        # add ch to logger
        log.addHandler(ch)

    def set_file_logger(self, log_level, path):
        """
        Convenience function to quickly configure any level of logging
        to a file.

        :type log_level: int
        :param log_level: A log level as specified in the `logging` module

        :type path: string
        :param path: Path to the log file.  The file will be created
            if it doesn't already exist.
        """
        log = logging.getLogger('botocore')
        log.setLevel(log_level)

        # create console handler and set level to debug
        ch = logging.FileHandler(path)
        ch.setLevel(log_level)

        # create formatter
        formatter = logging.Formatter(self.FmtString)

        # add formatter to ch
        ch.setFormatter(formatter)

        # add ch to logger
        log.addHandler(ch)


def get_session():
    """
    Return a new session  object.
    """
    return Session()
