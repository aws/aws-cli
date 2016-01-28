# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
This customization makes it easier to save various pieces of data
returned from iot commands that would typically need to be saved to a
file. This customization adds the following options:

- aws iot create-certificate-from-csr
  - ``--certificate-pem-outfile``: certificatePem
- aws iot create-keys-and-certificate
  - ``--certificate-pem-outfile``: certificatePem
  - ``--public-key-outfile``: keyPair.PublicKey
  - ``--private-key-outfile``: keyPair.PrivateKey
"""
from awscli.customizations.arguments import QueryOutFileArgument


def register_create_keys_and_cert_arguments(session, argument_table, **kwargs):
    """Add outfile save arguments to create-keys-and-certificate

    - ``--certificate-pem-outfile``
    - ``--public-key-outfile``
    - ``--private-key-outfile``
    """
    after_event = 'after-call.iot.CreateKeysAndCertificate'
    argument_table['certificate-pem-outfile'] = QueryOutFileArgument(
        session=session, name='certificate-pem-outfile',
        query='certificatePem', after_call_event=after_event, perm=0o600)
    argument_table['public-key-outfile'] = QueryOutFileArgument(
        session=session, name='public-key-outfile', query='keyPair.PublicKey',
        after_call_event=after_event, perm=0o600)
    argument_table['private-key-outfile'] = QueryOutFileArgument(
        session=session, name='private-key-outfile',
        query='keyPair.PrivateKey', after_call_event=after_event, perm=0o600)


def register_create_keys_from_csr_arguments(session, argument_table, **kwargs):
    """Add certificate-pem-outfile to create-certificate-from-csr"""
    argument_table['certificate-pem-outfile'] = QueryOutFileArgument(
        session=session, name='certificate-pem-outfile',
        query='certificatePem',
        after_call_event='after-call.iot.CreateCertificateFromCsr', perm=0o600)
