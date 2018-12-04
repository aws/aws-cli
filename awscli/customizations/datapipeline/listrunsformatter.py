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

from awscli.formatter import FullyBufferedFormatter


class ListRunsFormatter(FullyBufferedFormatter):
    TITLE_ROW_FORMAT_STRING = "       %-50.50s  %-19.19s  %-23.23s"
    FIRST_ROW_FORMAT_STRING = "%4d.  %-50.50s  %-19.19s  %-23.23s"
    SECOND_ROW_FORMAT_STRING = "       %-50.50s  %-19.19s  %-19.19s"

    def _format_response(self, command_name, response, stream):
        self._print_headers(stream)
        for i, obj in enumerate(response):
            self._print_row(i, obj, stream)

    def _print_headers(self, stream):
        stream.write(self.TITLE_ROW_FORMAT_STRING % (
            "Name", "Scheduled Start", "Status"))
        stream.write('\n')
        second_row = (self.SECOND_ROW_FORMAT_STRING % (
            "ID", "Started", "Ended"))
        stream.write(second_row)
        stream.write('\n')
        stream.write('-' * len(second_row))
        stream.write('\n')

    def _print_row(self, index, obj, stream):
        logical_name = obj['@componentParent']
        object_id = obj['@id']
        scheduled_start_date = obj.get('@scheduledStartTime', '')
        status = obj.get('@status', '')
        start_date = obj.get('@actualStartTime', '')
        end_date = obj.get('@actualEndTime', '')
        first_row = self.FIRST_ROW_FORMAT_STRING % (
            index + 1, logical_name, scheduled_start_date, status)
        second_row = self.SECOND_ROW_FORMAT_STRING % (
            object_id, start_date, end_date)
        stream.write(first_row)
        stream.write('\n')
        stream.write(second_row)
        stream.write('\n\n')
