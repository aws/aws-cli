# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

from awscli.customizations.configure import ConfigFileWriter
from awscli.customizations.emr.constants import EC2_ROLE_NAME
from awscli.customizations.emr.constants import EMR_ROLE_NAME

LOG = logging.getLogger(__name__)


def get_configs(session):
    return session.get_scoped_config().get('emr', {})


def get_current_profile_name(session):
    profile_name = session.get_config_variable('profile')
    return 'default' if profile_name is None else profile_name


def get_current_profile_var_name(session):
    return _get_profile_str(session, '.')


def _get_profile_str(session, separator):
    profile_name = session.get_config_variable('profile')
    return 'default' if profile_name is None \
        else 'profile%c%s' % (separator, profile_name)


def is_any_role_configured(session):
    parsed_configs = get_configs(session)
    return True if ('instance_profile' in parsed_configs
                    or 'service_role' in parsed_configs) \
        else False


def update_roles(session):
    if is_any_role_configured(session):
        LOG.debug("At least one of the roles is already associated with "
                  "your current profile ")
    else:
        config_writer = ConfigWriter(session)
        config_writer.update_config('service_role', EMR_ROLE_NAME)
        config_writer.update_config('instance_profile', EC2_ROLE_NAME)
        LOG.debug("Associated default roles with your current profile")


class ConfigWriter(object):

    def __init__(self, session):
        self.session = session
        self.section = _get_profile_str(session, ' ')
        self.config_file_writer = ConfigFileWriter()

    def update_config(self, key, value):
        config_filename = \
            os.path.expanduser(self.session.get_config_variable('config_file'))
        updated_config = {'__section__': self.section,
                          'emr': {key: value}}
        self.config_file_writer.update_config(updated_config, config_filename)
