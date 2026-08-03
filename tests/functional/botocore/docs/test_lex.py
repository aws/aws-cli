# Copyright 2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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


class TestLexDocs(BaseDocsFunctionalTest):
    TYPE_STRING = '{...}|[...]|123|123.4|\'string\'|True|None'

    def test_jsonheader_docs(self):
        docs = self.get_docstring_for_method('lex-runtime', 'post_content')
        self.assert_contains_lines_in_order(
            [
                '**Request Syntax**',
                f'sessionAttributes={self.TYPE_STRING},',
                ':type sessionAttributes: JSON serializable',
                '**Response Syntax**',
                f'\'slots\': {self.TYPE_STRING},',
                f'\'sessionAttributes\': {self.TYPE_STRING}',
                '**slots** (JSON serializable)',
                '**sessionAttributes** (JSON serializable)',
            ],
            docs,
        )
