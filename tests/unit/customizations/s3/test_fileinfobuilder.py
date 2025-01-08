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
from awscli.testutils import unittest
from awscli.customizations.s3.filegenerator import FileStat
from awscli.customizations.s3.fileinfo import FileInfo
from awscli.customizations.s3.fileinfobuilder import FileInfoBuilder


class TestFileInfoBuilder(unittest.TestCase):
    def test_info_setter(self):
        info_setter = FileInfoBuilder(client='client',
                                      source_client='source_client',
                                      parameters='parameters',
                                      is_stream='is_stream')
        files = [FileStat(src='src', dest='dest', compare_key='compare_key',
                          size='size', last_update='last_update',
                          src_type='src_type', dest_type='dest_type',
                          operation_name='operation_name',
                          response_data='associated_response_data')]
        file_infos = info_setter.call(files)
        for file_info in file_infos:
            attributes = file_info.__dict__.keys()
            for key in attributes:
                self.assertEqual(getattr(file_info, key), str(key))

    def test_swaps_clients_for_sync_delete(self):
        client_name = 'client'
        source_client_name = 'source_client'
        info_setter = FileInfoBuilder(client=client_name,
                                      source_client=source_client_name,
                                      parameters={'delete': True},
                                      is_stream='is_stream')
        files = [FileStat(src='src', dest='dest', compare_key='compare_key',
                          size='size', last_update='last_update',
                          src_type='src_type', dest_type='dest_type',
                          operation_name='delete')]
        file_infos = info_setter.call(files)
        for file_info in file_infos:
            self.assertEqual(file_info.client, source_client_name)
            self.assertEqual(file_info.source_client, client_name)

if __name__ == "__main__":
    unittest.main()
