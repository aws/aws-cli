# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from tests.functional.docs import BaseDocsFunctionalTest
from tests.functional.test_alias import ALIAS_CASES


class TestAliasesDocumented(BaseDocsFunctionalTest):
    def test_all_aliases_are_documented_correctly(self):
        for case in ALIAS_CASES:
            content = self.get_docstring_for_method(
                case['service'], case['operation']
            ).decode('utf-8')
            new_name = case['new_name']
            original_name = case['original_name']
            param_name_template = ':param %s:'
            param_type_template = ':type %s:'
            param_example_template = '%s='

            # Make sure the new parameters are in the documentation
            # but the old names are not.
            self.assertIn(param_name_template % new_name, content)
            self.assertIn(param_type_template % new_name, content)
            self.assertIn(param_example_template % new_name, content)

            self.assertNotIn(param_name_template % original_name, content)
            self.assertNotIn(param_type_template % original_name, content)
            self.assertNotIn(param_example_template % original_name, content)
