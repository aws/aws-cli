# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import sys


def lazy_call(import_name, **kwargs):
    """Import a callable and invoke it with the provided kwargs.

    :param import_name: A dotted string of the form ``package.module.Callable``.
    :type import_name: string
    :param kwargs: kwargs to pass to the callable once it's imported.
    :type kwargs:  dict

    """
    module_name, callable_name = import_name.rsplit('.', 1)
    __import__(module_name)
    module = sys.modules[module_name]
    return getattr(module, callable_name)(**kwargs)


class LazyClientCreator(object):
    """Lazy create a botocore client.

    This class will defer creating a client until the create_client method
    is invoked.  It will also avoid importing botocore until we need to
    create a client.

    Importing botocore and creating a botocore session/client is an expensive
    process, and we only want to do this when we know for sure that we need
    a client.  This class manages this process.

    """
    def __init__(self,
                 import_name='awscli.clidriver.create_clidriver'):
        self._import_name = import_name
        self._session_cache = {}

    def create_client(self, service_name, parsed_region=None,
                      parsed_profile=None, **kwargs):
        if self._session_cache.get(parsed_profile) is None:
            session = self.create_session()
            session.set_config_variable('profile', parsed_profile)
            self._session_cache[parsed_profile] = session
        self._session_cache[parsed_profile].set_config_variable(
            'region', parsed_region)
        return self._session_cache[parsed_profile].create_client(
                                                        service_name, **kwargs)

    def create_session(self):
        return lazy_call(self._import_name).session
