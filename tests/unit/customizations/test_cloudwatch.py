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
import decimal

from awscli.testutils import unittest

import mock

from awscli.customizations import putmetricdata


class TestPutMetricArgument(unittest.TestCase):
    def test_build_metric_name_arg(self):
        arg = putmetricdata.PutMetricArgument('metric-name',
                                              help_text='metric-name')
        parameters = {}
        arg.add_to_params(parameters, 'MyMetricName')
        self.assertEqual(parameters['MetricData'][0]['MetricName'],
                         'MyMetricName')

    def test_build_unit_arg(self):
        arg = putmetricdata.PutMetricArgument('unit',
                                              help_text='unit')
        parameters = {}
        arg.add_to_params(parameters, 'Percent')
        self.assertEqual(parameters['MetricData'][0]['Unit'],
                         'Percent')

    def test_value_arg(self):
        arg = putmetricdata.PutMetricArgument('value',
                                              help_text='value')
        parameters = {}
        arg.add_to_params(parameters, '123.1')
        self.assertEqual(parameters['MetricData'][0]['Value'],
                         decimal.Decimal('123.1'))

    def test_timestamp_arg(self):
        arg = putmetricdata.PutMetricArgument('timestamp',
                                              help_text='timestamp')
        parameters = {}
        arg.add_to_params(parameters, '2013-09-01')
        self.assertEqual(parameters['MetricData'][0]['Timestamp'],
                         '2013-09-01')

    def test_dimensions_arg(self):
        arg = putmetricdata.PutMetricArgument('dimensions',
                                              help_text='dimensions')
        parameters = {}
        arg.add_to_params(parameters, 'User=someuser,Stack=test')
        self.assertEqual(parameters['MetricData'][0]['Dimensions'],
                         [{"Name": "User", "Value": "someuser"},
                          {"Name": "Stack", "Value": "test"}])

    def test_statistics_arg(self):
        arg = putmetricdata.PutMetricArgument('statistic-values',
                                              help_text='statistic-values')
        parameters = {}
        arg.add_to_params(parameters,
                          'Sum=250,Minimum=30,Maximum=70,SampleCount=5')
        self.assertEqual(parameters['MetricData'][0]['StatisticValues'],
                         {'Maximum': decimal.Decimal('70'),
                          'Minimum': decimal.Decimal('30'),
                          'SampleCount': decimal.Decimal('5'),
                          'Sum': decimal.Decimal('250')})

    def test_parse_empty_value(self):
        arg = putmetricdata.PutMetricArgument('dimensions',
                                              help_text='dimensions')
        parameters = {}
        arg.add_to_params(parameters, None)
        self.assertEqual(parameters, {})
