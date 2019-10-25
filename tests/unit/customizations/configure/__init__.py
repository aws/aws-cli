# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from botocore.exceptions import ProfileNotFound


class FakeConfigStore(object):
    def set_config_provider(self, *args, **kwargs):
        pass


class FakeSession(object):

    def __init__(self, all_variables, profile_does_not_exist=False,
                 config_file_vars=None, environment_vars=None,
                 credentials=None, profile=None, available_profiles=None):
        self.variables = all_variables
        self.profile_does_not_exist = profile_does_not_exist
        self.config = {}
        if config_file_vars is None:
            config_file_vars = {}
        self.config_file_vars = config_file_vars
        if environment_vars is None:
            environment_vars = {}
        if available_profiles is None:
            available_profiles = ['default']
        self._available_profiles = available_profiles
        self.environment_vars = environment_vars
        self._credentials = credentials
        self.profile = profile

    @property
    def available_profiles(self):
        return self._available_profiles

    def get_credentials(self):
        return self._credentials

    def get_scoped_config(self):
        if self.profile_does_not_exist:
            raise ProfileNotFound(profile='foo')
        return self.config

    def get_component(self, component, *args, **kwargs):
        if component == 'config_store':
            return FakeConfigStore()

    def get_config_variable(self, name, methods=None):
        if name == 'credentials_file':
            # The credentials_file var doesn't require a
            # profile to exist.
            return '~/fake_credentials_filename'
        if self.profile_does_not_exist and not name == 'config_file':
            raise ProfileNotFound(profile='foo')
        if methods is not None:
            if 'env' in methods:
                return self.environment_vars.get(name)
            elif 'config' in methods:
                return self.config_file_vars.get(name)
        else:
            return self.variables.get(name)

    def emit(self, event_name, **kwargs):
        pass

    def emit_first_non_none_response(self, *args, **kwargs):
        pass

    def _build_profile_map(self):
        if self.full_config is None:
            return None
        return self.full_config['profiles']
