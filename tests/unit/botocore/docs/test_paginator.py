# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from botocore.docs.paginator import PaginatorDocumenter
from botocore.paginate import PaginatorModel
from tests.unit.docs import BaseDocsTest


class TestPaginatorDocumenter(BaseDocsTest):
    def setUp(self):
        super().setUp()
        self.add_shape_to_params('Biz', 'String')
        self.extra_setup()

    def extra_setup(self):
        self.setup_client()
        paginator_model = PaginatorModel(self.paginator_json_model)
        self.paginator_documenter = PaginatorDocumenter(
            client=self.client,
            service_paginator_model=paginator_model,
            root_docs_path=self.root_services_path,
        )

    def test_document_paginators(self):
        self.paginator_documenter.document_paginators(self.doc_structure)
        self.assert_contains_lines_in_order(
            [
                '==========',
                'Paginators',
                '==========',
                'The available paginators are:',
                'paginator/SampleOperation',
            ]
        )
        self.assert_contains_lines_in_order(
            [
                '.. py:class:: MyService.Paginator.SampleOperation',
                '  ::',
                '    paginator = client.get_paginator(\'sample_operation\')',
                '  .. py:method:: paginate(**kwargs)',
                (
                    '    Creates an iterator that will paginate through responses'
                    ' from :py:meth:`MyService.Client.sample_operation`.'
                ),
                '    **Request Syntax**',
                '    ::',
                '      response_iterator = paginator.paginate(',
                '          Biz=\'string\',',
                '          PaginationConfig={',
                '              \'MaxItems\': 123,',
                '              \'PageSize\': 123,',
                '              \'StartingToken\': \'string\'',
                '          }',
                '      )',
                '    :type Biz: string',
                '    :param Biz:',
                '    :type PaginationConfig: dict',
                '    :param PaginationConfig:',
                (
                    '      A dictionary that provides parameters to '
                    'control pagination.'
                ),
                '      - **MaxItems** *(integer) --*',
                '      - **PageSize** *(integer) --*',
                '      - **StartingToken** *(string) --*',
                '    :rtype: dict',
                '    :returns:',
                '      **Response Syntax**',
                '      ::',
                '        {',
                '            \'Biz\': \'string\',',
                '            \'NextToken\': \'string\'',
                '        }',
                '      **Response Structure**',
                '      - *(dict) --*',
                '        - **Biz** *(string) --*',
                '        - **NextToken** *(string) --*',
            ],
            self.get_nested_service_contents(
                'myservice', 'paginator', 'SampleOperation'
            ),
        )

    def test_no_page_size_if_no_limit_key(self):
        paginator = self.paginator_json_model["pagination"]
        operation = paginator["SampleOperation"]
        del operation["limit_key"]

        self.paginator_documenter.document_paginators(self.doc_structure)
        self.assert_not_contains_lines(
            [
                '              \'PageSize\': 123,',
                '      - **PageSize** *(integer) --*',
            ]
        )
