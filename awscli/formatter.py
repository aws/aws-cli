# Copyright 2012-2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.

# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at

#     http://aws.amazon.com/apache2.0/

# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import sys
import json

import six

from awscli.table import MultiTable, Styler, ColorizedStyler


class Formatter(object):

    def __init__(self, args):
        pass


class JSONFormatter(Formatter):

    def __call__(self, operation, response):
        json_response = json.dumps(response, indent=4)
        print(json_response)


class TableFormatter(Formatter):
    """Pretty print a table from a given response.

    The table formatter is able to take any generic response
    and generate a pretty printed table.  It does this without
    using the output definition from the model.

    """
    def __init__(self, args, table=None):
        if args.color == 'auto':
            self.table = MultiTable(initial_section=False,
                                    column_separator='|')
        elif args.color == 'off':
            styler = Styler()
            self.table = MultiTable(initial_section=False,
                                    column_separator='|', styler=styler)
        elif args.color == 'on':
            styler = ColorizedStyler()
            self.table = MultiTable(initial_section=False,
                                    column_separator='|', styler=styler,
                                    auto_reformat=True)
        else:
            raise ValueError("Unknown color option: %s" % args.color)

    def __call__(self, operation, response, stream=sys.stdout):
        self._build_table(operation.name, response)
        try:
            self.table.render(stream)
        except IOError:
            # If they're piping stdout to another process which exits before
            # we're done writing all of our output, we'll get an error about a
            # closed pipe which we can safely ignore.
            pass


    def _build_table(self, title, current, indent_level=0):
        if not current:
            return
        self.table.new_section(title, indent_level=indent_level)
        if isinstance(current, list):
            if isinstance(current[0], dict):
                self._build_sub_table_from_list(current, indent_level, title)
            else:
                for item in current:
                    self.table.add_row([item])
        if isinstance(current, dict):
            # Render a single row section with keys as header
            # and the row as the values, unless the value
            # is a list.
            self._build_sub_table_from_dict(current, indent_level)

    def _build_sub_table_from_dict(self, current, indent_level):
        # Render a single row section with keys as header
        # and the row as the values, unless the value
        # is a list.
        headers, more = self._group_scalar_keys(current)
        if len(headers) == 1:
            # Special casing if a dict has a single scalar key/value pair.
            self.table.add_row([headers[0], current[headers[0]]])
        elif headers:
            self.table.add_row_header(headers)
            self.table.add_row([current[k] for k in headers])
        for remaining in more:
            self._build_table(remaining, current[remaining],
                              indent_level=indent_level + 1)

    def _build_sub_table_from_list(self, current, indent_level, title):
        headers, more = self._group_scalar_keys(current[0])
        self.table.add_row_header(headers)
        first = True
        for element in current:
            if not first and more:
                self.table.new_section(title,
                                       indent_level=indent_level)
                self.table.add_row_header(headers)
            first = False
            self.table.add_row([element[header] for header in headers])
            for remaining in more:
                self._build_table(remaining, element[remaining],
                                  indent_level=indent_level + 1)

    def _scalar_type(self, element):
        return not isinstance(element, (list, dict))

    def _group_scalar_keys(self, current):
        # Given a dict, separate the keys into those whose values are
        # scalar, and those whose values aren't.  Return two lists,
        # one is the scalar value keys, the second is the remaining keys.
        more = []
        headers = []
        for element in current:
            if self._scalar_type(current[element]):
                headers.append(element)
            else:
                more.append(element)
        headers.sort()
        more.sort()
        return headers, more


class TextFormatter(Formatter):

    def _output(self, data, label=None):
        """
        A very simple, very stupid text formatter that has no
        knowledge of the output as defined in the JSON model.
        """
        if isinstance(data, dict):
            scalars = []
            non_scalars = []
            for key, val in data.items():
                if isinstance(val, dict):
                    non_scalars.append((key, val))
                elif isinstance(val, list):
                    non_scalars.append((key, val))
                elif not isinstance(val, six.string_types):
                    scalars.append(str(val))
                else:
                    scalars.append(val)
            if label:
                scalars.insert(0, label.upper())
            print('\t'.join(scalars))
            for label, non_scalar in non_scalars:
                self._output(non_scalar, label)
        elif isinstance(data, list):
            for d in data:
                self._output(d)

    def __call__(self, operation, response):
        self._output(response)


def get_formatter(format_type, args):
    if format_type == 'json':
        return JSONFormatter(args)
    elif format_type == 'text':
        return TextFormatter(args)
    elif format_type == 'table':
        return TableFormatter(args)
    return None
