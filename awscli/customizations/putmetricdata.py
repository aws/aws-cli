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
"""
This customization adds the following scalar parameters to the
cloudwatch put-metric-data operation:

* --metric-name
* --dimensions
* --timestamp
* --value
* --statistic-values
* --unit

"""
import decimal

from awscli.arguments import CustomArgument
from awscli.utils import split_on_commas
from awscli.customizations.utils import validate_mutually_exclusive_handler


def register_put_metric_data(event_handler):
    event_handler.register('building-argument-table.cloudwatch.put-metric-data',
                           _promote_args)
    event_handler.register(
        'operation-args-parsed.cloudwatch.put-metric-data',
        validate_mutually_exclusive_handler(
            ['metric_data'], ['metric_name', 'timestamp', 'unit', 'value',
                              'dimensions', 'statistic_values']))


def _promote_args(argument_table, **kwargs):
    # We're providing top level params for metric-data.  This means
    # that metric-data is now longer a required arg.  We do need
    # to check that either metric-data or the complex args we've added
    # have been provided.
    argument_table['metric-data'].required = False

    argument_table['metric-name'] = PutMetricArgument(
        'metric-name', help_text='The name of the metric.')
    argument_table['timestamp'] = PutMetricArgument(
        'timestamp', help_text='The time stamp used for the metric.  '
                               'If not specified, the default value is '
                               'set to the time the metric data was '
                               'received.')
    argument_table['unit'] = PutMetricArgument(
        'unit', help_text='The unit of metric.')
    argument_table['value'] = PutMetricArgument(
        'value', help_text='The value for the metric.  Although the --value '
                           'parameter accepts numbers of type Double, '
                           'Amazon CloudWatch truncates values with very '
                           'large exponents.  Values with base-10 exponents '
                           'greater than 126 (1 x 10^126) are truncated.  '
                           'Likewise, values with base-10 exponents less '
                           'than -130 (1 x 10^-130) are also truncated.')

    argument_table['dimensions'] = PutMetricArgument(
        'dimensions', help_text=(
            'The --dimensions argument further expands '
            'on the identity of a metric using a Name=Value '
            'pair, separated by commas, for example: '
            '<code>--dimensions InstanceID=1-23456789 InstanceType=m1.small</code>. '
            'Note that the <code>--dimensions</code> argument has a different '
            'format when used in <code>get-metric-data</code>, where for the same example you would '
            'use the format <code>--dimensions Name=InstanceID,Value=i-aaba32d4 Name=InstanceType,value=m1.small </code>.'))
    argument_table['statistic-values'] = PutMetricArgument(
        'statistic-values', help_text='A set of statistical values describing '
                                      'the metric.')


def insert_first_element(name):
    def _wrap_add_to_params(func):
        def _add_to_params(self, parameters, value):
            if value is None:
                return
            if name not in parameters:
                # We're taking a shortcut here and assuming that the first
                # element is a struct type, hence the default value of
                # a dict.  If this was going to be more general we'd need
                # to have this paramterized, i.e. you pass in some sort of
                # factory function that creates the initial starting value.
                parameters[name] = [{}]
            first_element = parameters[name][0]
            return func(self, first_element, value)
        return _add_to_params
    return _wrap_add_to_params


class PutMetricArgument(CustomArgument):
    def add_to_params(self, parameters, value):
        method_name = '_add_param_%s' % self.name.replace('-', '_')
        return getattr(self, method_name)(parameters, value)

    @insert_first_element('MetricData')
    def _add_param_metric_name(self, first_element, value):
        first_element['MetricName'] = value

    @insert_first_element('MetricData')
    def _add_param_unit(self, first_element, value):
        first_element['Unit'] = value

    @insert_first_element('MetricData')
    def _add_param_timestamp(self, first_element, value):
        first_element['Timestamp'] = value

    @insert_first_element('MetricData')
    def _add_param_value(self, first_element, value):
        # Use a Decimal to avoid loss in precision.
        first_element['Value'] = decimal.Decimal(value)

    @insert_first_element('MetricData')
    def _add_param_dimensions(self, first_element, value):
        # Dimensions needs a little more processing.  We support
        # the key=value,key2=value syntax so we need to parse
        # that.
        dimensions = []
        for pair in split_on_commas(value):
            key, value = pair.split('=')
            dimensions.append({'Name': key, 'Value': value})
        first_element['Dimensions'] = dimensions

    @insert_first_element('MetricData')
    def _add_param_statistic_values(self, first_element, value):
        # StatisticValues is a struct type so we are parsing
        # a csv keyval list into a dict.
        statistics = {}
        for pair in split_on_commas(value):
            key, value = pair.split('=')
            # There are four supported values: Maximum, Minimum, SampleCount,
            # and Sum.  All of them are documented as a type double so we can
            # convert these to a decimal value to preserve precision.
            statistics[key] = decimal.Decimal(value)
        first_element['StatisticValues'] = statistics
