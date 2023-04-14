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
from mock import Mock, call
from datetime import datetime, timedelta
from dateutil import parser, tz

from awscli.customizations.cloudtrail import utils
from awscli.testutils import unittest
from awscli.customizations.cloudtrail.utils import (
    normalize_date,
    format_date,
    parse_date,
    PublicKeyProvider,
)


START_DATE = parser.parse("20140810T000000Z")


class TestCloudTrailUtils(unittest.TestCase):
    def test_gets_account_id_from_arn(self):
        arn = "foo:bar:baz:qux:1234"
        self.assertEqual("1234", utils.get_account_id_from_arn(arn))

    def test_gets_trail_by_arn(self):
        cloudtrail_client = Mock()
        cloudtrail_client.describe_trails.return_value = {
            "trailList": [
                {"TrailARN": "a", "Foo": "Baz"},
                {"TrailARN": "b", "Foo": "Bar"},
            ]
        }
        result = utils.get_trail_by_arn(cloudtrail_client, "b")
        self.assertEqual("Bar", result["Foo"])

    def test_throws_when_unable_to_get_trail_by_arn(self):
        cloudtrail_client = Mock()
        cloudtrail_client.describe_trails.return_value = {"trailList": []}
        self.assertRaises(ValueError, utils.get_trail_by_arn, cloudtrail_client, "b")

    def test_formats_dates(self):
        date = datetime(2015, 8, 21, tzinfo=tz.tzutc())
        self.assertEqual("20150821T000000Z", format_date(date))

    def test_parses_dates_with_better_error_message(self):
        try:
            parse_date("foo")
            self.fail("Should have failed to parse")
        except ValueError as e:
            self.assertIn("Unable to parse date value: foo", str(e))

    def test_parses_dates(self):
        date = parse_date("August 25, 2015 00:00:00 UTC")
        self.assertEqual(date, datetime(2015, 8, 25, tzinfo=tz.tzutc()))

    def test_normalizes_date_timezones(self):
        date = datetime(2015, 8, 21, tzinfo=tz.tzlocal())
        normalized = normalize_date(date)
        self.assertEqual(tz.tzutc(), normalized.tzinfo)


class TestPublicKeyProvider(unittest.TestCase):
    def test_returns_public_keys_in_range(self):
        cloudtrail_client = Mock()
        cloudtrail_client.list_public_keys.return_value = {
            "PublicKeyList": [
                {"Fingerprint": "a", "OtherData": "a", "Value": "a"},
                {"Fingerprint": "b", "OtherData": "b", "Value": "b"},
                {"Fingerprint": "c", "OtherData": "c", "Value": "c"},
            ]
        }
        provider = PublicKeyProvider(cloudtrail_client)
        start_date = START_DATE
        end_date = start_date + timedelta(days=2)
        keys = provider.get_public_keys(start_date, end_date)
        self.assertEqual(
            {
                "a": {"Fingerprint": "a", "OtherData": "a", "Value": "a"},
                "b": {"Fingerprint": "b", "OtherData": "b", "Value": "b"},
                "c": {"Fingerprint": "c", "OtherData": "c", "Value": "c"},
            },
            keys,
        )
        cloudtrail_client.list_public_keys.assert_has_calls(
            [call(EndTime=end_date, StartTime=start_date)]
        )

    def test_returns_public_key_in_range(self):
        cloudtrail_client = Mock()
        cloudtrail_client.list_public_keys.return_value = {
            "PublicKeyList": [
                {"Fingerprint": "a", "OtherData": "a1", "Value": "a2"},
                {"Fingerprint": "b", "OtherData": "b1", "Value": "b2"},
                {"Fingerprint": "c", "OtherData": "c1", "Value": "c2"},
            ]
        }
        provider = PublicKeyProvider(cloudtrail_client)
        start_date = parser.parse("20140810T000000Z")
        public_key = provider.get_public_key(start_date, "c")
        self.assertEqual("c2", public_key)

    def test_key_not_found(self):
        with self.assertRaises(RuntimeError):
            cloudtrail_client = Mock()
            cloudtrail_client.list_public_keys.return_value = {
                "PublicKeyList": [
                    {"Fingerprint": "123", "OtherData": "456", "Value": "789"},
                ]
            }
            provider = PublicKeyProvider(cloudtrail_client)
            start_date = parser.parse("20140810T000000Z")
            provider.get_public_key(start_date, "c")
