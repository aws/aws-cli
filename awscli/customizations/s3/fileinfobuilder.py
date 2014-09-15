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
from awscli.customizations.s3.fileinfo import FileInfo


class FileInfoBuilder(object):
    """
    This class takes a ``FileBase`` object's attributes and generates
    a ``FileInfo`` object so that the operation can be performed.
    """
    def __init__(self, service, endpoint, source_endpoint=None,
                 parameters = None, is_stream=False):
        self._service = service
        self._endpoint = endpoint
        self._source_endpoint = endpoint
        if source_endpoint:
            self._source_endpoint = source_endpoint
        self._parameters = parameters
        self._is_stream = is_stream 

    def call(self, files):
        for file_base in files:
            file_info = self._inject_info(file_base)
            yield file_info            

    def _inject_info(self, file_base):
        file_info_attr = {}
        file_info_attr['src'] = file_base.src
        file_info_attr['dest'] = file_base.dest
        file_info_attr['compare_key'] = file_base.compare_key
        file_info_attr['size'] = file_base.size
        file_info_attr['last_update'] = file_base.last_update
        file_info_attr['src_type'] = file_base.src_type
        file_info_attr['dest_type'] = file_base.dest_type
        file_info_attr['operation_name'] = file_base.operation_name
        file_info_attr['service'] = self._service
        file_info_attr['endpoint'] = self._endpoint
        file_info_attr['source_endpoint'] = self._source_endpoint
        file_info_attr['parameters'] = self._parameters
        file_info_attr['is_stream'] = self._is_stream
        return FileInfo(**file_info_attr)
