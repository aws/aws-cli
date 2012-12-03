# Copyright (c) 2012 Mitch Garnaat http://garnaat.org/
# Copyright 2012 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import os
from six.moves import configparser
import requests
import json
import logging
import exceptions

logger = logging.getLogger(__name__)


class Credentials(object):
    """
    Holds the credentials needed to authenticate requests.  In addition
    the Credential object knows how to search for credentials and how
    to choose the right credentials when multiple credentials are found.

    :ivar access_key: The access key part of the credentials.
    :ivar secret_key: The secret key part of the credentials.
    :ivar token: The security token, valid only for session credentials.
    :ivar profiles: A list of available credentials profiles.
    :ivar method: A string which identifies where the credentials
        were found.  Valid values are: iam_role|env|config|boto.
    :ivar config_path: If the method is `config` this contains the fully
        qualified path to the config file used.
    """

    def __init__(self, access_key=None, secret_key=None, token=None):
        self.access_key = access_key
        self.secret_key = secret_key
        self.token = token
        self.method = None
        self.config_path = None
        self.profiles = []


def _search_md(url='http://169.254.169.254/latest/meta-data/iam/'):
    d = {}
    try:
        r = requests.get(url, timeout=.1)
        if r.content:
            fields = r.content.split('\n')
            for field in fields:
                if field.endswith('/'):
                    d[field[0:-1]] = get_iam_role(url + field)
                else:
                    val = requests.get(url + field).content
                    if val[0] == '{':
                        val = json.loads(val)
                    else:
                        p = val.find('\n')
                        if p > 0:
                            val = r.content.split('\n')
                    d[field] = val
    except (requests.Timeout, requests.ConnectionError):
        pass
    return d


def search_iam_role(**kwargs):
    if 'metadata' in kwargs:
        # to help with unit tests
        metadata = kwargs['metadata']
    else:
        metadata = _search_md()
    # Assuming there's only one role on the instance profile.
    if metadata:
        metadata = metadata['iam']['security-credentials'].values()[0]
        credentials = Credentials(metadata['AccessKeyId'],
                                  metadata['SecretAccessKey'],
                                  metadata['Token'])
        credentials.method = 'iam-role'
        return credentials
    else:
        return None


def search_environment(**kwargs):
    """
    Search for credentials in explicit environment variables.
    """
    credentials = None
    access_key = os.environ.get('AWS_ACCESS_KEY_ID', None)
    secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY', None)
    if access_key and secret_key:
        credentials = Credentials(access_key, secret_key)
        credentials.method = 'env'
    return credentials


def search_file(**kwargs):
    """
    If the 'AWS_CONFIG_FILE' environment variable exists, parse that
    file for credentials.
    """
    if 'AWS_CONFIG_FILE' in os.environ:
        profile = kwargs.get('profile', 'default')
        access_key_name = kwargs['access_key_name']
        secret_key_name = kwargs['secret_key_name']
        access_key = secret_key = None
        path = os.getenv('AWS_CONFIG_FILE')
        path = os.path.expandvars(path)
        path = os.path.expanduser(path)
        cp = configparser.RawConfigParser()
        credentials = None
        try:
            cp.read(path)
            if not cp.has_section(profile):
                msg = 'The profile (%s) could not be found' % profile
                logger.warning(msg)
            else:
                access_key = None
                if cp.has_option(profile, access_key_name):
                    access_key = cp.get(profile, access_key_name)
                secret_key = None
                if cp.has_option(profile, secret_key_name):
                    secret_key = cp.get(profile, secret_key_name)
                if access_key and secret_key:
                    credentials = Credentials(access_key, secret_key)
                    credentials.profiles.extend(cp.sections())
                    credentials.method = 'config'
                    credentials.config_path = path
        except configparser.Error:
            msg = 'Unable to parse config file: %s' % path
            logger.warning(msg)
        except:
            msg = 'Unknown error encountered parsing: %s' % path
            logger.warning(msg)
        return credentials


def search_boto_config(**kwargs):
    """
    Look for credentials in boto config file.
    I'm leaving this off the search path for now to avoid confusion.
    """
    credentials = access_key = secret_key = None
    if 'BOTO_CONFIG' in os.environ:
        paths = [os.environ['BOTO_CONFIG']]
    else:
        paths = ['/etc/boto.cfg', '~/.boto']
    paths = [os.path.expandvars(p) for p in paths]
    paths = [os.path.expanduser(p) for p in paths]
    cp = configparser.RawConfigParser()
    cp.read(paths)
    if cp.has_section('Credentials'):
        access_key = cp.get('Credentials', 'aws_access_key_id')
        secret_key = cp.get('Credentials', 'aws_secret_access_key')
    if access_key and secret_key:
        credentials = Credentials(access_key, secret_key)
        credentials.method = 'boto'
    return credentials

AllCredentialFunctions = [search_environment,
                          search_file,
                          search_boto_config,
                          search_iam_role]


def get_credentials(profile=None, metadata=None):
    if not profile:
        profile = 'default'
    for cred_fn in AllCredentialFunctions:
        credentials = cred_fn(profile=profile,
                              access_key_name='aws_access_key_id',
                              secret_key_name='aws_secret_access_key',
                              metadata=metadata)
        if credentials:
            break
    if not credentials:
        msg = 'No credentials could be found'
        raise exceptions.NoCredentialsError(msg)
    return credentials
