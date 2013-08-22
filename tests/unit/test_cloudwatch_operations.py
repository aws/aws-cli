#!/usr/bin/env python
# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from decimal import Decimal
from tests import TestParamSerialization

import botocore.session
from botocore.exceptions import ValidationError


class TestCloudwatchOperations(TestParamSerialization):

    def assert_is_valid_float_value(self, value):
        # We don't really care about the specific operation,
        # just that an operation that has a float param
        # can accept the specified value passed in.
        # We're using put-metric-data as the operation here.
        input_metric_data = [
            {"MetricName": "FreeMemoryBytes", "Dimensions": [],
             "Unit": "Bytes",
             "Timestamp": "2013-07-30T00:58:11.284Z",
             # The "Value" param is specified as type "float"
             # in the model.
             "Value": value}]
        serialized_params = {
            'MetricData.member.1.MetricName':
            'FreeMemoryBytes',
            'MetricData.member.1.Timestamp':
                '2013-07-30T00:58:11.284000+00:00',
            'MetricData.member.1.Unit': 'Bytes',
            'MetricData.member.1.Value': str(value),
            'Namespace': 'System/Linux'
        }
        self.assert_params_serialize_to(
            'cloudwatch.PutMetricData',
            input_params={'namespace': 'System/Linux',
                          'metric_data': input_metric_data},
            serialized_params=serialized_params)

    def test_float_validation(self):
        self.assert_is_valid_float_value(9130160128.0)

    def test_integers_allowed_for_floats(self):
        self.assert_is_valid_float_value(9130160128)

    def test_string_type_is_allowed(self):
        self.assert_is_valid_float_value("9130160128.123")

    def test_decimal_type_is_allowed(self):
        self.assert_is_valid_float_value(Decimal("9130160128.123"))

    def test_bad_float_value(self):
        bad_value = 'notafloat'
        input_metric_data = [
            {"MetricName": "FreeMemoryBytes", "Dimensions": [],
             "Unit": "Bytes",
             "Timestamp": "2013-07-30T00:58:11.284Z",
             "Value": bad_value}]
        op = self.session.get_service(
            'cloudwatch').get_operation('PutMetricData')
        with self.assertRaises(ValidationError):
            op.build_parameters(namespace='System/Linux',
                                metric_data=input_metric_data)
        # Empty dict is also a bad value for a float param.
        input_metric_data[0]['Value'] = {}
        with self.assertRaises(ValidationError):
            op.build_parameters(namespace='System/Linux',
                                metric_data=input_metric_data)
