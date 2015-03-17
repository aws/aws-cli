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
import sys
import os

from botocore.handlers import disable_signing
import jmespath

from awscli.compat import urlparse


def register_parse_global_args(cli):
    cli.register('top-level-args-parsed', resolve_types)
    cli.register('top-level-args-parsed', no_sign_request)


def resolve_types(parsed_args, **kwargs):
    # This emulates the "type" arg from argparse, but does so in a way
    # that plugins can also hook into this process.
    _resolve_arg(parsed_args, 'query')
    _resolve_arg(parsed_args, 'verify_ssl')
    _resolve_arg(parsed_args, 'endpoint_url')


def _resolve_arg(parsed_args, name):
    value = getattr(parsed_args, name, None)
    if value is not None:
        new_value = getattr(sys.modules[__name__], '_resolve_%s' % name)(value)
        setattr(parsed_args, name, new_value)


def _resolve_query(value):
    try:
        return jmespath.compile(value)
    except Exception as e:
        raise ValueError("Bad value for --query %s: %s" % (value, str(e)))


def _resolve_verify_ssl(value):
    verify = None
    if not value:
        verify = False
    else:
        verify = os.environ.get('AWS_CA_BUNDLE')
    return verify


def _resolve_endpoint_url(value):
    parsed = urlparse.urlparse(value)
    # Our http library requires you specify an endpoint url
    # that contains a scheme, so we'll verify that up front.
    if not parsed.scheme:
        raise ValueError('Bad value for --endpoint-url "%s": scheme is '
                         'missing.  Must be of the form '
                         'http://<hostname>/ or https://<hostname>/' % value)
    return value


def no_sign_request(parsed_args, session, **kwargs):
    if not parsed_args.sign_request:
        # In order to make signing disabled for all requests
        # we need to use botocore's ``disable_signing()`` handler.
        session.register('choose-signer', disable_signing)
