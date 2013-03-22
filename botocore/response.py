# Copyright (c) 2012-2013 Mitch Garnaat http://garnaat.org/
# Copyright 2012-2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish, dis-
# tribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the fol-
# lowing conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABIL-
# ITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
# SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
"""
This module uses the SAX parser to turn response XML into Python
native datastructures.

We create an Element object for each XML element we encounter in
the response data.

"""
import xml.etree.cElementTree
import json
import logging
from botocore import ScalarTypes

logger = logging.getLogger(__name__)


class Response(object):

    _log_path = None

    @classmethod
    def set_log_path(cls, path):
        cls._log_path = path

    @classmethod
    def log_xml(cls, operation, xml):
        if cls._log_path:
            file_name = '%s-%s.xml' % (operation.service.cli_name,
                                       operation.cli_name)
            path = os.path.join(cls._log_path, file_name)
            fp = open(path, 'w')
            fp.write(xml)
            fp.close()

    @classmethod
    def log_data(cls, operation, data):
        if cls._log_path:
            file_name = '%s-%s.json' % (operation.service.cli_name,
                                        operation.cli_name)
            path = os.path.join(cls._log_path, file_name)
            fp = open(path, 'w')
            json.dump(data, fp, indent=4)
            fp.close()

    def __init__(self, operation):
        self.operation = operation
        self.value = None

    def parse(self, s):
        pass

    def get_value(self):
        return self.value


class XmlResponse(Response):

    def __init__(self, operation):
        Response.__init__(self, operation)
        self.tree = None
        self.value = {}

    def parse(self, s):
        self.log_xml(self.operation, s)
        self.tree = xml.etree.cElementTree.fromstring(s)
        self.build_value()
        self.log_data(self.operation, self.get_value())

    def clark_notation(self, tag):
        return '{%s}%s' % (self.operation.service.xmlnamespace, tag)

    def _do_structure(self, name, element, defn):
        data = {}
        for member_name in defn['members']:
            member_defn = defn['members'][member_name]
            xmlname = member_defn.get('xmlname', member_name)
            cn = self.clark_notation(xmlname)
            subelement = element.find(cn)
            if subelement is None:
                subelement = element.find('*/%s' % cn)
            if subelement is not None:
                data[member_name] = self._build_value(member_name,
                                                      subelement,
                                                      member_defn)
        return data

    def _do_list(self, name, element, defn):
        if 'flattened' in defn and defn['flattened']:
            xmlname = defn['members'].get('xmlname', name)
            cn = self.clark_notation(xmlname)
            subelements = element.findall('.//%s' % cn)
        else:
            xmlname = defn['members'].get('xmlname', 'member')
            cn = self.clark_notation(xmlname)
            subelements = element.findall(cn)
        return [self._build_value(name, subelement, defn['members'])
                for subelement in subelements]

    def _do_map(self, name, element, defn):
        xmlname = defn.get('xmlname', 'entry')
        cn = self.clark_notation(xmlname)
        if 'flattened' in defn and defn['flattened']:
            entry_elements = element.findall('*/%s' % cn)
        else:
            entry_elements = element.findall(cn)
        data = {}
        for entry_element in entry_elements:
            key_xmlname = defn['keys'].get('xmlname', 'key')
            cn = self.clark_notation(key_xmlname)
            key_element = entry_element.find(cn)
            value_xmlname = defn['members'].get('xmlname', 'value')
            cn = self.clark_notation(value_xmlname)
            value_element = entry_element.find(cn)
            data[key_element.text] = self._build_value(xmlname,
                                                       value_element,
                                                       defn['members'])
        return data

    def check_children(self, element):
        kids = list(element)
        if len(kids) == 1:
            element = kids[0]
        elif len(kids) > 1:
            logger.debug('ermahgerd')
        return element

    def _do_string(self, name, element, defn):
        element = self.check_children(element)
        rval = element.text
        kids = element.getchildren()
        if rval is not None:
            rval = rval.strip()
        return rval

    _do_timestamp = _do_string

    def _do_integer(self, name, element, defn):
        element = self.check_children(element)
        return int(element.text)

    _do_long = _do_integer

    def _do_float(self, name, element, defn):
        element = self.check_children(element)
        return float(element.text)

    _do_double = _do_float

    def _do_boolean(self, name, element, defn):
        element = self.check_children(element)
        return True if element.text.lower() == 'true' else False

    def _build_value(self, name, element, defn):
        rval = None
        if element is not None:
            handler_name = '_do_%s' % defn['type']
            if hasattr(self, handler_name):
                rval = getattr(self, handler_name)(name, element, defn)
            else:
                print('Unhandled type: %s' % defn['type'])
        return rval

    def get_response_metadata(self):
        rmd = {}
        self.value['ResponseMetadata'] = rmd
        request_id = self.tree.find(self.clark_notation('requestId'))
        if request_id is None:
            xpath = '*/%s' % self.clark_notation('RequestId')
            request_id = self.tree.find(xpath)
        if request_id is not None:
            rmd['RequestId'] = request_id.text.strip()

    def build_value(self):
        for member_name in self.operation.output['members']:
            member_defn = self.operation.output['members'][member_name]
            if 'flattened' in member_defn and member_defn['flattened']:
                subelement = self.tree
            else:
                xmlname = member_defn.get('xmlname', member_name)
                xpath = './/%s' % self.clark_notation(xmlname)
                subelement = self.tree.find(xpath)
            value = self._build_value(member_name, subelement, member_defn)
            if value is not None:
                self.value[member_name] = value
        self.get_response_metadata()


class JSONResponse(Response):

    def parse(self, s):
        try:
            self.value = json.loads(s)
        except:
            logger.debug('Error loading JSON response body')


class StreamingResponse(Response):

    def __init__(self, operation):
        Response.__init__(self, operation)
        self.value = {}

    def parse(self, headers, stream):
        for member_name in self.operation.output['members']:
            member_dict = self.operation.output['members'][member_name]
            if member_dict.get('location') == 'header':
                header_name = member_dict.get('location_name')
                if header_name and header_name in headers:
                    self.value[member_name] = headers[header_name]
            elif member_dict.get('type') == 'blob':
                if member_dict.get('payload'):
                    if member_dict.get('streaming'):
                        self.value[member_name] = stream


def get_response(operation, http_response):
    encoding = 'utf-8'
    if http_response.encoding:
        encoding = http_response.encoding
    content_type = http_response.headers['content-type']
    if content_type and ';' in content_type:
        content_type = content_type.split(';')[0]
    logger.debug('content-type=%s' % content_type)
    if operation.is_streaming():
        streaming_response = StreamingResponse(operation)
        streaming_response.parse(http_response.headers, http_response.raw)
        return (http_response, streaming_response.get_value())
    body = http_response.text.encode(encoding.lower())
    logger.debug(body)
    if content_type in ('application/x-amz-json-1.0',
                        'application/x-amz-json-1.1', 'application/json'):
        json_response = JSONResponse(operation)
        json_response.parse(body)
        return (http_response, json_response.get_value())
    # We are defaulting to an XML response handler because many query
    # services send XML error responses but do not include a Content-Type
    # header.
    xml_response = XmlResponse(operation)
    xml_response.parse(body)
    return (http_response, xml_response.get_value())
