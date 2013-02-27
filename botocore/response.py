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
import xml.sax
import json
import logging
from botocore import ScalarTypes

logger = logging.getLogger(__name__)


class Response(object):

    def __init__(self, operation):
        self.operation = operation
        self.value = None

    def parse(self, s):
        pass

    def get_value(self):
        return self.value


class Element(object):

    def __init__(self, name, defn):
        self.name = name
        self.defn = defn
        self.value = ''
        if self.defn:
            if self.defn['type'] == 'list':
                self.value = []
            elif self.defn['type'] in ('structure', 'map'):
                self.value = {}
        self.key_name = None
        self.to_be_flattened = False

    def __repr__(self):
        if self.defn:
            type_name = self.defn['type']
        else:
            type_name = 'generic'
        return '%s(%s)=%s' % (self.name, type_name, self.value)

    def set_value(self, name, value):
        if self.defn:
            if self.defn['type'] == 'integer':
                self.value = int(value)
            elif self.defn['type'] == 'float':
                self.value = float(value)
            elif self.defn['type'] == 'boolean':
                if value.lower() == 'true':
                    self.value = True
                else:
                    self.value = False
            elif self.defn['type'] in ScalarTypes:
                self.value = value
            elif self.defn['type'] == 'list':
                if self.to_be_flattened:
                    if self.defn['members']['type'] == 'structure':
                        self.value[-1][name] = value
                    else:
                        self.value.append(value)
                else:
                    self.value.append(value)
            elif self.defn['type'] == 'map':
                if self.to_be_flattened:
                    self.value = value
                else:
                    key_name = self.defn['keys'].get('xmlname', 'key')
                    if name == key_name:
                        self.key_name = value
                    else:
                        self.value[self.key_name] = value
            elif self.defn['type'] == 'structure':
                self.value[name] = value
        else:
            if not name:
                self.value = value
            else:
                if not isinstance(self.value, dict):
                    self.value = {}
                self.value[name] = value


class XmlResponse(Response, xml.sax.ContentHandler):

    def __init__(self, operation):
        Response.__init__(self, operation)
        self.root_element = Element('root', None)
        self.stack = [self.root_element]
        self.current_text = ''
        self.type_map = {}
        self.build_type_map(None, self.operation.output)
        self.map_map = {}
        self.flattened_map = {}
        self.create_key_names(None, operation.output)

    def create_key_names(self, name, type_dict):
        if type_dict:
            if name:
                type_dict['key_name'] = name
            if type_dict['type'] == 'structure':
                for member_name in type_dict['members']:
                    self.create_key_names(member_name,
                                          type_dict['members'][member_name])
            elif type_dict['type'] == 'list':
                self.create_key_names(None, type_dict['members'])
            elif type_dict['type'] == 'map':
                self.create_key_names(None, type_dict['keys'])
                self.create_key_names(None, type_dict['members'])

    def build_type_map(self, name, type_dict):
        if not isinstance(type_dict, dict):
            return
        if not name:
            if 'shape_name' in type_dict:
                name = type_dict['shape_name']
        name = type_dict.get('xmlname', name)
        if type_dict['type'] == 'structure':
            self.type_map[name] = type_dict
            for member_name in type_dict['members']:
                self.build_type_map(member_name,
                                    type_dict['members'][member_name])
        elif type_dict['type'] == 'list':
            flattened = type_dict.get('flattened', False)
            if flattened:
                name = type_dict['members'].get('xmlname', name)
            self.type_map[name] = type_dict
            self.build_type_map(None, type_dict['members'])
        elif type_dict['type'] == 'map':
            self.type_map[name] = type_dict
            self.build_type_map('key', type_dict['keys'])
            self.build_type_map('value', type_dict['members'])
        else:
            if name not in self.type_map:
                self.type_map[name] = type_dict

    def get_value(self):
        return self.root_element.value

    def add_element(self, name):
        new_element = None
        if name in self.map_map:
            self.stack.append(self.map_map[name])
        current_element = self.stack[-1]
        if name in self.flattened_map:
            new_element_name = name
            new_element = self.flattened_map[name]
            if new_element.defn['type'] == 'list':
                if new_element.defn['members']['type'] == 'structure':
                    new_element.value.append({})
        elif not current_element.defn:
            for type_name in self.type_map:
                type_dict = self.type_map[type_name]
                xmlname = type_dict.get('xmlname', type_name)
                if xmlname == name:
                    new_element = Element(xmlname, type_dict)
                    new_element_name = xmlname
                    if type_dict['type'] == 'list':
                        flattened = type_dict.get('flattened', False)
                        if flattened:
                            new_element.to_be_flattened = True
                            self.flattened_map[new_element_name] = new_element
                            if new_element.defn['type'] == 'list':
                                if new_element.defn['members']['type'] == 'structure':
                                    new_element.value.append({})
        else:
            if current_element.defn['type'] == 'structure':
                for member_name in current_element.defn['members']:
                    data = current_element.defn['members'][member_name]
                    xmlname = data.get('xmlname', member_name)
                    if name == xmlname:
                        new_element = Element(xmlname, data)
                        new_element_name = xmlname
            elif current_element.defn['type'] == 'map':
                if name in self.map_map:
                    return self.map_map[name]
                flattened = current_element.defn.get('flattened', False)
                if not flattened and name == 'entry':
                    new_element = Element('entry', current_element.defn)
                    new_element_name = 'entry'
                    current_element.to_be_flattened = True
                else:
                    # Is this a key?
                    data = current_element.defn['keys']
                    xmlname = data.get('xmlname', 'key')
                    if name == xmlname:
                        new_element = Element(xmlname, data)
                        new_element_name = xmlname
                    else:
                        # Or a value?
                        data = current_element.defn['members']
                        xmlname = data.get('xmlname', 'value')
                        if name == xmlname:
                            new_element = Element(xmlname, data)
                            new_element_name = xmlname
            elif current_element.defn['type'] == 'list':
                if current_element.defn.get('flattened'):
                    member_data = current_element.defn['members']
                    for member_name in member_data['members']:
                        data = member_data['members'][member_name]
                        xmlname = data.get('xmlname', member_name)
                        if name == xmlname:
                            new_element = Element(xmlname, data)
                            new_element_name = xmlname
                else:
                    data = current_element.defn['members']
                    xmlname = data.get('xmlname', 'member')
                    if name == xmlname or current_element.defn.get('flattened'):
                        new_element = Element(xmlname, data)
                        new_element_name = xmlname
        if new_element is None:
            new_element = Element(name, None)
            new_element_name = name
        self.stack.append(new_element)
        if new_element.defn and new_element.defn['type'] == 'map':
            self.map_map[name] = new_element

    def startElement(self, name, attrs):
        self.current_text = ''
        if name.startswith(self.operation.name):
            pass
        else:
            self.add_element(name)

    def endElement(self, name):
        if name.startswith(self.operation.name):
            pass
        else:
            current_element = self.stack.pop()
            self.current_text = self.current_text.strip()
            if self.current_text:
                current_element.set_value(None, self.current_text)
                self.current_text = ''
            parent_element = self.stack[-1]
            real_name = name
            if current_element.defn:
                if 'key_name' in current_element.defn:
                    real_name = current_element.defn['key_name']
            parent_element.set_value(real_name, current_element.value)

    def characters(self, content):
        self.current_text += content

    def parse(self, s):
        if s:
            xml.sax.parseString(s, self)


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
    if content_type in ('application/x-amz-json-1.1', 'application/json'):
        json_response = JSONResponse(operation)
        json_response.parse(body)
        return (http_response, json_response.get_value())
    # We are defaulting to an XML response handler because many query
    # services send XML error responses but do not include a Content-Type
    # header.
    xml_response = XmlResponse(operation)
    xml_response.parse(body)
    return (http_response, xml_response.get_value())
