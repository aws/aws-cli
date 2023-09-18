# Copyright 2012-2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

from dateutil import tz, parser
from datetime import timedelta

DATE_FORMAT = "%Y%m%dT%H%M%SZ"


def get_account_id_from_arn(trail_arn):
    """Gets the account ID portion of an ARN"""
    return trail_arn.split(":")[4]


def get_trail_by_arn(cloudtrail_client, trail_arn):
    """Gets trail information based on the trail's ARN"""
    trails = cloudtrail_client.describe_trails()["trailList"]
    for trail in trails:
        if trail.get("TrailARN", None) == trail_arn:
            return trail
    raise ValueError("A trail could not be found for %s" % trail_arn)


def format_date(date):
    """Returns a formatted date string in a CloudTrail date format"""
    return date.strftime(DATE_FORMAT)


def normalize_date(date):
    """Returns a normalized date using a UTC timezone"""
    return date.replace(tzinfo=tz.tzutc())


def parse_date(date_string):
    try:
        return parser.parse(date_string)
    except ValueError:
        raise ValueError("Unable to parse date value: %s" % date_string)


class PublicKeyProvider:
    """Retrieves public key from CloudTrail with Fingerprint (ID)."""

    def __init__(self, cloudtrail_client):
        self._cloudtrail_client = cloudtrail_client

    def get_public_keys(self, start_date, end_date):
        """Loads public keys in a date range into a returned dict.

        :type start_date: datetime
        :param start_date: Start date of a date range.
        :type end_date: datetime
        :param end_date: End date of a date range.
        :rtype: dict
        :return: Returns a dict where each key is the fingerprint of the
            public key, and each value is a dict of public key data.
        """
        public_keys = self._cloudtrail_client.list_public_keys(
            StartTime=start_date, EndTime=end_date
        )
        public_keys_in_range = public_keys["PublicKeyList"]
        return dict((key["Fingerprint"], key) for key in public_keys_in_range)

    def get_public_key(self, signature_generate_time, public_key_fingerprint):
        """Loads public key that been used in a specific time.

        :type signature_generate_time: datetime
        :param signature_generate_time: Time for the key been used for signing.
        :type public_key_fingerprint: string
        :param public_key_fingerprint: Fingerprint (ID) of a public key.

        :rtype: string
        :return: Return the public key value.
        """
        search_end_date = format_date(
            normalize_date(signature_generate_time + timedelta(days=20))
        )
        public_keys = self._cloudtrail_client.list_public_keys(
            StartTime=signature_generate_time, EndTime=search_end_date
        )
        public_keys_in_range = public_keys["PublicKeyList"]
        for key in public_keys_in_range:
            if key["Fingerprint"] == public_key_fingerprint:
                return key["Value"]

        raise RuntimeError(
            "No public keys found for key with fingerprint: %s" % public_key_fingerprint
        )
