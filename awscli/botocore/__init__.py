# Copyright (c) 2012-2013 Mitch Garnaat http://garnaat.org/
# Copyright 2012-2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

import logging
import os
import re

__version__ = '2.0.0dev155'


class NullHandler(logging.Handler):
    def emit(self, record):
        pass

# Configure default logger to do nothing
log = logging.getLogger('botocore')
log.addHandler(NullHandler())


_first_cap_regex = re.compile('(.)([A-Z][a-z]+)')
_end_cap_regex = re.compile('([a-z0-9])([A-Z])')
# The regex below handles the special case where some acronym
# name is pluralized, e.g GatewayARNs, ListWebACLs, SomeCNAMEs.
_special_case_transform = re.compile('[A-Z]{2,}s$')
# Prepopulate the cache with special cases that don't match
# our regular transformation.
_xform_cache = {
    ('CreateCachediSCSIVolume', '_'): 'create_cached_iscsi_volume',
    ('CreateCachediSCSIVolume', '-'): 'create-cached-iscsi-volume',
    ('DescribeCachediSCSIVolumes', '_'): 'describe_cached_iscsi_volumes',
    ('DescribeCachediSCSIVolumes', '-'): 'describe-cached-iscsi-volumes',
    ('DescribeStorediSCSIVolumes', '_'): 'describe_stored_iscsi_volumes',
    ('DescribeStorediSCSIVolumes', '-'): 'describe-stored-iscsi-volumes',
    ('CreateStorediSCSIVolume', '_'): 'create_stored_iscsi_volume',
    ('CreateStorediSCSIVolume', '-'): 'create-stored-iscsi-volume',
    ('ListHITsForQualificationType', '_'): 'list_hits_for_qualification_type',
    ('ListHITsForQualificationType', '-'): 'list-hits-for-qualification-type',
    ('ExecutePartiQLStatement', '_'): 'execute_partiql_statement',
    ('ExecutePartiQLStatement', '-'): 'execute-partiql-statement',
    ('ExecutePartiQLTransaction', '_'): 'execute_partiql_transaction',
    ('ExecutePartiQLTransaction', '-'): 'execute-partiql-transaction',
    ('ExecutePartiQLBatch', '_'): 'execute_partiql_batch',
    ('ExecutePartiQLBatch', '-'): 'execute-partiql-batch',
    (
        'AssociateWhatsAppBusinessAccount',
        '_',
    ): 'associate_whatsapp_business_account',
    (
        'AssociateWhatsAppBusinessAccount',
        '-',
    ): 'associate-whatsapp-business-account',
    ('DeleteWhatsAppMessageMedia', '_'): 'delete_whatsapp_media_message',
    ('DeleteWhatsAppMessageMedia', '-'): 'delete-whatsapp-media-message',
    ('DisassociateWhatsAppBusinessAccount', '_'): 'disassociate_whatsapp_business_account',
    ('DisassociateWhatsAppBusinessAccount', '-'):'disassociate-whatsapp-business-account',
    ('GetLinkedWhatsAppBusinessAccount', '_'): 'get_linked_whatsapp_business_account',
    ('GetLinkedWhatsAppBusinessAccount', '-'): 'get-linked-whatsapp-business-account',
    ('GetLinkedWhatsAppBusinessAccountPhoneNumber', '_'): 'get_linked_whatsapp_business_account_phone_number',
    ('GetLinkedWhatsAppBusinessAccountPhoneNumber', '-'): 'get-linked-whatsapp-business-account-phone-number',
    ('GetWhatsAppMessageMedia', '_'): 'get_whatsapp_message_media',
    ('GetWhatsAppMessageMedia', '-'): 'get-whatsapp-message-media',
    ('ListLinkedWhatsAppBusinessAccounts', '_'): 'list_linked_whatsapp_business_accounts',
    ('ListLinkedWhatsAppBusinessAccounts', '-'): 'list-linked-whatsapp-business-accounts',
    ('PostWhatsAppMessageMedia', '_'): 'post_whatsapp_message_media',
    ('PostWhatsAppMessageMedia', '-'): 'post-whatsapp-message-media',
    ('PutWhatsAppBusinessAccountEventDestinations', '_'): 'put_whatsapp_business_account_event_destinations',
    ('PutWhatsAppBusinessAccountEventDestinations', '-'): 'put-whatsapp-business-account-event-destinations',
    ('SendWhatsAppMessage', '_'): 'send_whatsapp_message',
    ('SendWhatsAppMessage', '-'): 'send-whatsapp-message',
}
ScalarTypes = ('string', 'integer', 'boolean', 'timestamp', 'float', 'double')

BOTOCORE_ROOT = os.path.realpath(os.path.dirname(os.path.abspath(__file__)))


# Used to specify anonymous (unsigned) request signature
class UNSIGNED(object):
    def __copy__(self):
        return self

    def __deepcopy__(self, memodict):
        return self


UNSIGNED = UNSIGNED()


def xform_name(name, sep='_', _xform_cache=_xform_cache):
    """Convert camel case to a "pythonic" name.

    If the name contains the ``sep`` character, then it is
    returned unchanged.

    """
    if sep in name:
        # If the sep is in the name, assume that it's already
        # transformed and return the string unchanged.
        return name
    key = (name, sep)
    if key not in _xform_cache:
        if _special_case_transform.search(name) is not None:
            is_special = _special_case_transform.search(name)
            matched = is_special.group()
            # Replace something like ARNs, ACLs with _arns, _acls.
            name = name[:-len(matched)] + sep + matched.lower()
        s1 = _first_cap_regex.sub(r'\1' + sep + r'\2', name)
        transformed = _end_cap_regex.sub(r'\1' + sep + r'\2', s1).lower()
        _xform_cache[key] = transformed
    return _xform_cache[key]
