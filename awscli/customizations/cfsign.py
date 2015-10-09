# Should go into botocore/cloudfront.py

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
import json
from base64 import b64encode
try:
    maketrans = bytes.maketrans  # For Python 3
except:
    from string import maketrans

import rsa


LOG = logging.getLogger(__name__)


def cloudfront_b64encode(content):
    return b64encode(content).translate(maketrans(b'+=/', b'-_~'))


def sign(url, key_id, private_key, expires, starts=None, ip_address=None):
    """
    Creates a signed CloudFront URL.

    :type url: str
    :param url: The URL of the protected object.

    :type key_id: str
    :param key_id: The CloudFront Key Pair ID

    :type private_key: str
    :param private_key: The private key string used for signing.

    :type expires: int
    :param expires: The expiry time of the URL. Format is a unix epoch.

    :type starts: int
    :param starts: The expiry time of the URL. Format is a unix epoch.

    :type ip_address: str
    :param ip_address: Use 'x.x.x.x' for an IP, or 'x.x.x.x/x' for a subnet.

    :rtype: str
    :return: The signed URL.
    """
    # SEE: http://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-creating-signed-url-custom-policy.html
    condition = {"DateLessThan": {"AWS:EpochTime": int(expires)}}
    if ip_address:
        ip_address = ip_address if '/' in ip_address else (ip_address + '/32')
        condition["IpAddress"] = {"AWS:SourceIp": ip_address}
    if starts:
        condition["DateGreaterThan"] = {"AWS:EpochTime": int(starts)}
    custom_policy = {"Statement": [{"Resource": url, "Condition": condition}]}
    compact_policy = json.dumps(
        custom_policy,
        sort_keys=True,  # Otherwise test cases become unstable on Python3
        separators=(',', ':')).encode('utf8')
    LOG.debug("Policy = %s", compact_policy)
    rsa_pk = rsa.PrivateKey.load_pkcs1(private_key.encode('utf8'))
    signed_policy = rsa.sign(compact_policy, rsa_pk, 'SHA-1')
    return url + ('&' if '?' in url else '?') + '&'.join([
        'Policy=%s' % cloudfront_b64encode(compact_policy).decode('utf8'),
        'Signature=%s' % cloudfront_b64encode(signed_policy).decode('utf8'),
        'Key-Pair-Id=%s' % key_id,
        ])
