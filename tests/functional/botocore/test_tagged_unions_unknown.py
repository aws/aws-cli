# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from botocore.session import Session
from tests import unittest


class TestTaggedUnionsUnknown(unittest.TestCase):
    def test_tagged_union_member_name_does_not_coincide_with_unknown_key(self):
        # This test ensures that operation models do not use SDK_UNKNOWN_MEMBER
        # as a member name. Thereby reserving SDK_UNKNOWN_MEMBER for the parser to
        # set as a key on the reponse object. This is necessary when the client
        # encounters a member that it is unaware of or not modeled.
        session = Session()
        for service_name in session.get_available_services():
            service_model = session.get_service_model(service_name)
            for shape_name in service_model.shape_names:
                shape = service_model.shape_for(shape_name)
                if hasattr(shape, 'is_tagged_union') and shape.is_tagged_union:
                    self.assertNotIn('SDK_UNKNOWN_MEMBER', shape.members)
