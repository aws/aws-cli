# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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


class FileInfo(object):
    """This class contains important details related to performing a task.

    It can perform operations such as ``upload``, ``download``, ``copy``,
    ``delete``, ``move``.  Similarly to ``TaskInfo`` objects attributes
    like ``session`` need to be set in order to perform operations.

    :param dest: the destination path
    :type dest: string
    :param compare_key: the name of the file relative to the specified
        directory/prefix.  This variable is used when performing syncing
        or if the destination file is adopting the source file's name.
    :type compare_key: string
    :param size: The size of the file in bytes.
    :type size: integer
    :param last_update: the local time of last modification.
    :type last_update: datetime object
    :param dest_type: if the destination is s3 or local.
    :param dest_type: string
    :param parameters: a dictionary of important values this is assigned in
        the ``BasicTask`` object.
    :param associated_response_data: The response data used by
        the ``FileGenerator`` to create this task. It is either an dictionary
        from the list of a ListObjects or the response from a HeadObject. It
        will only be filled if the task was generated from an S3 bucket.
    """
    def __init__(self, src, dest=None, compare_key=None, size=None,
                 last_update=None, src_type=None, dest_type=None,
                 operation_name=None, client=None, parameters=None,
                 source_client=None, is_stream=False,
                 associated_response_data=None):
        self.src = src
        self.src_type = src_type
        self.operation_name = operation_name
        self.client = client
        self.dest = dest
        self.dest_type = dest_type
        self.compare_key = compare_key
        self.size = size
        self.last_update = last_update
        # Usually inject ``parameters`` from ``BasicTask`` class.
        self.parameters = {}
        if parameters is not None:
            self.parameters = parameters
        self.source_client = source_client
        self.is_stream = is_stream
        self.associated_response_data = associated_response_data

    def is_glacier_compatible(self):
        """Determines if a file info object is glacier compatible

        Operations will fail if the S3 object has a storage class of GLACIER
        and it involves copying from S3 to S3, downloading from S3, or moving
        where S3 is the source (the delete will actually succeed, but we do
        not want fail to transfer the file and then successfully delete it).

        :returns: True if the FileInfo's operation will not fail because the
            operation is on a glacier object. False if it will fail.
        """
        if self._is_glacier_object(self.associated_response_data):
            if self.operation_name in ['copy', 'download']:
                return False
            elif self.operation_name == 'move':
                if self.src_type == 's3':
                    return False
        return True

    def _is_glacier_object(self, response_data):
        glacier_storage_classes = ['GLACIER', 'DEEP_ARCHIVE']
        if response_data:
            if response_data.get('StorageClass') in glacier_storage_classes \
                    and not self._is_restored(response_data):
                return True
        return False

    def _is_restored(self, response_data):
        # Returns True is this is a glacier object that has been
        # restored back to S3.
        # 'Restore' looks like: 'ongoing-request="false", expiry-date="..."'
        return 'ongoing-request="false"' in response_data.get('Restore', '')
