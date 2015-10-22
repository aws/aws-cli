# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

from botocore import model

from awscli.arguments import BaseCLIArgument


logger = logging.getLogger(__name__)


DEFAULT = 1
HELP = """
<p>Number of instances to launch. If a single number is provided, it
is assumed to be the minimum to launch (defaults to %d).  If a range is
provided in the form <code>min:max</code> then the first number is
interpreted as the minimum number of instances to launch and the second
is interpreted as the maximum number of instances to launch.</p>""" % DEFAULT


def register_count_events(event_handler):
    event_handler.register(
        'building-argument-table.ec2.run-instances', ec2_add_count)
    event_handler.register(
        'before-parameter-build.ec2.RunInstances', set_default_count)


def ec2_add_count(argument_table, **kwargs):
    argument_table['count'] = CountArgument('count')
    del argument_table['min-count']
    del argument_table['max-count']


def set_default_count(params, **kwargs):
    params.setdefault('MaxCount', DEFAULT)
    params.setdefault('MinCount', DEFAULT)


class CountArgument(BaseCLIArgument):

    def __init__(self, name):
        self.argument_model = model.Shape('CountArgument', {'type': 'string'})
        self._name = name
        self._required = False

    @property
    def cli_name(self):
        return '--' + self._name

    @property
    def cli_type_name(self):
        return 'string'

    @property
    def required(self):
        return self._required

    @required.setter
    def required(self, value):
        self._required = value

    @property
    def documentation(self):
        return HELP

    def add_to_parser(self, parser):
        # We do NOT set default value here. It will be set later by event hook.
        parser.add_argument(self.cli_name, metavar=self.py_name,
                            help='Number of instances to launch')

    def add_to_params(self, parameters, value):
        if value is None:
            # NO-OP if value is not explicitly set by user
            return
        try:
            if ':' in value:
                minstr, maxstr = value.split(':')
            else:
                minstr, maxstr = (value, value)
            parameters['MinCount'] = int(minstr)
            parameters['MaxCount'] = int(maxstr)
        except:
            msg = ('count parameter should be of '
                   'form min[:max] (e.g. 1 or 1:10)')
            raise ValueError(msg)
