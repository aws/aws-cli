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


class Formatter(object):

    def __init__(self):
        pass


class JSONFormatter(Formatter):

    def __call__(self, operation, response):
        json_response = json.dumps(response, indent=4)
        print(json_response)


class TableFormatter(Formatter):

    def label(self, s, n):
        separator = '+' + '-+-'.join(['-' * n]) + '+'
        format = "%%-%ds" % n
        pattern = '|' + format + '|'
        print(separator)
        print(pattern % s.center(n))

    def _output(self, d, label=None):
        values = []
        sub_dicts = []
        sub_lists = []
        headers = []
        for key in d:
            val = d[key]
            if isinstance(val, dict):
                sub_dicts.append((key, val))
            elif isinstance(val, list):
                sub_lists.append((key, val))
            else:
                values.append(str(val))
                headers.append(key)
        lens = [(len(h) + 2) for h in headers]
        for i in range(len(values)):
            if len(values[i]) + 2 > lens[i]:
                lens[i] = len(values[i]) + 2
        print('Total length=%d' % sum(lens))
        formats = []
        hformats = []
        for i in range(len(values)):
            formats.append("%%-%ds" % lens[i])
            hformats.append("%%-%ds" % lens[i])
        pattern = '|' + '|'.join(formats) + '|'
        hpattern = '|' + '|'.join(hformats) + '|'
        separator = '+' + '+'.join(['-' * n for n in lens]) + '+'
        h = []
        v = []
        for i in range(len(headers)):
            h.append(headers[i].center(lens[i]))
        if label:
            self.label(label, (sum(lens) + len(lens) - 1))
        print(separator)
        print(hpattern % tuple(h))
        print(separator)
        v = []
        for i in range(len(values)):
            v.append(values[i].center(lens[i]))
        print(pattern % tuple(v))
        print(separator)
        if sub_dicts:
            for label, sub_dict in sub_dicts:
                self._output(sub_dict, label)
        if sub_lists:
            for label, sub_list in sub_lists:
                for item in sub_list:
                    if isinstance(item, dict):
                        self._output(item, label)

    def _output1(self, l):
        """
        Print a list of similar dictionaries.  Headers are extracted
        from the keys of the first dictionary.
        """
        print(l)
        values = []
        sub_dicts = []
        sub_lists = []
        for d in l:
            v = []
            headers = []
            for key in d:
                val = d[key]
                if isinstance(val, dict):
                    sub_dicts.append(val)
                elif isinstance(val, list):
                    sub_lists.append(val)
                else:
                    v.append(str(val))
                    headers.append(key)
            values.append(v)
        lens = [(len(h) + 2) for h in headers]
        for vl in values:
            for i in range(len(vl)):
                if len(vl[i]) + 2 > lens[i]:
                    lens[i] = len(vl[i]) + 2
        formats = []
        hformats = []
        for i in range(len(values[0])):
            formats.append("%%-%ds" % lens[i])
            hformats.append("%%-%ds" % lens[i])
        pattern = '|' + " | ".join(formats) + '|'
        hpattern = '|' + ' | '.join(hformats) + '|'
        separator = '+' + '-+-'.join(['-' * n for n in lens]) + '+'
        h = []
        v = []
        for i in range(len(headers)):
            h.append(headers[i].center(lens[i]))
        print(separator)
        print(hpattern % tuple(h))
        print(separator)
        for vl in values:
            v = []
            for i in range(len(vl)):
                v.append(vl[i].center(lens[i]))
            print(pattern % tuple(v))
            print(separator)
        if sub_dicts:
            self._output(sub_dicts)
        if sub_lists:
            for sub_list in sub_lists:
                self._output(sub_list)

    def __call__(self, operation, response):
        self._output(response)


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


def get_formatter(format_type):
    if format_type == 'json':
        return JSONFormatter()
    if format_type == 'text':
        return TextFormatter()
    return None
