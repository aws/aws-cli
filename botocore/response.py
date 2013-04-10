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
import sys
import xml.etree.cElementTree
from botocore import ScalarTypes
import json
import logging

logger = logging.getLogger(__name__)


class Response(object):

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
        self.element_map = {}
        self.value = {}
        self._parent = None

    def clark_notation(self, tag):
        return '{%s}%s' % (self.operation.service.xmlnamespace, tag)

    def get_element_base_tag(self, elem):
        if '}' in elem.tag:
            elem_tag = elem.tag.split('}')[1]
        else:
            elem_tag = elem.tag
        return elem_tag

    def parse(self, s):
        self.tree = xml.etree.cElementTree.fromstring(s)
        if self.operation.output:
            self.build_element_map(self.operation.output, 'root')
        self.start(self.tree)

    def get_response_metadata(self):
        rmd = {}
        self.value['ResponseMetadata'] = rmd
        rmd_elem = self.tree.find(self.clark_notation('ResponseMetadata'))
        if rmd_elem is not None:
            rmd_elem.tail = True
            request_id = rmd_elem.find(self.clark_notation('RequestId'))
        else:
            request_id = self.tree.find(self.clark_notation('requestId'))
        if request_id is not None:
            request_id.tail = True
            rmd['RequestId'] = request_id.text.strip()

    def build_element_map(self, defn, keyname):
        xmlname = defn.get('xmlname', keyname)
        if not xmlname:
            xmlname = defn.get('shape_name')
        self.element_map[xmlname] = defn
        if defn['type'] == 'structure':
            for member_name in defn['members']:
                self.build_element_map(defn['members'][member_name],
                                         member_name)
        elif defn['type'] == 'list':
            self.build_element_map(defn['members'], None)
        elif defn['type'] == 'map':
            self.build_element_map(defn['keys'], 'key')
            self.build_element_map(defn['members'], 'value')

    def find(self, parent, tag):
        tag = tag.split(':')[-1]
        cn = self.clark_notation(tag)
        child = parent.find(cn)
        if child is None:
            child = parent.find('*/%s' % cn)
        return child

    def findall(self, parent, tag):
        cn = self.clark_notation(tag)
        children = parent.findall(cn)
        if not children:
            try:
                children = parent.findall('*/%s' % cn)
            except:
                pass
        return children

    def parent_slow(self, elem, target):
        for child in elem:
            if child == target:
                self._parent = elem
                break
            self.parent_slow(child, target)

    def parent(self, elem):
        # We need the '..' operator in XPath but only that is only
        # available in Python versions >= 2.7
        if sys.version_info[0] == 2 and sys.version_info[1] == 6:
            self.parent_slow(self.tree, elem)
            parent = self._parent
            self._parent = None
        else:
            parent = self.tree.find('.//%s/..' % elem.tag)
        return parent

    def get_elem_text(self, elem):
        data = elem.text
        if data is not None:
            data = elem.text.strip()
        return data

    def _handle_string(self, elem, shape):
        data = self.get_elem_text(elem)
        if not data:
            children = list(elem)
            if len(children) == 1:
                data = self.get_elem_text(children[0])
        return data

    _handle_timestamp = _handle_string

    def _handle_integer(self, elem, shape):
        data = self.get_elem_text(elem)
        if data:
            data = int(data)
        return data

    _handle_long = _handle_integer

    def _handle_float(self, elem, shape):
        data = self.get_elem_text(elem)
        if data:
            data = float(data)
        return data

    _handle_double = _handle_float

    def _handle_boolean(self, elem, shape):
        return True if elem.text.lower() == 'true' else False

    def _handle_structure(self, elem, shape):
        new_data = {}
        for member_name in shape['members']:
            member_shape = shape['members'][member_name]
            xmlname = member_shape.get('xmlname', member_name)
            child = self.find(elem, xmlname)
            if child is not None:
                new_data[member_name] = self.handle_elem(child, member_shape)
            else:
                logger.debug('unable to find struct member: %s' % xmlname)
        return new_data

    def _handle_list(self, elem, shape):
        xmlname = shape['members'].get('xmlname', 'member')
        children = self.findall(elem, xmlname)
        if not children and shape.get('flattened'):
            parent = self.parent(elem)
            if parent is not None:
                tagname = self.get_element_base_tag(elem)
                children = self.findall(parent, tagname)
        if not children:
            children = []
        return [self.handle_elem(child, shape['members'])
                for child in children]

    def _handle_map(self, elem, shape):
        data = {}
        # First collect all map entries
        xmlname = shape.get('xmlname', 'entry')
        keyshape = shape['keys']
        valueshape = shape['members']
        key_xmlname = keyshape.get('xmlname', 'key')
        value_xmlname = valueshape.get('xmlname', 'value')
        members = self.findall(elem, xmlname)
        if not members:
            parent = self.parent(elem)
            if parent is not None:
                members = self.findall(parent, xmlname)
        for member in members:
            key = self.find(member, key_xmlname)
            value = self.find(member, value_xmlname)
            cn = self.clark_notation(value_xmlname)
            value = member.find(cn)
            data[self.handle_elem(key, keyshape)] = self.handle_elem(value,
                                                                     valueshape)
        return data

    def handle_elem(self, elem, shape):
        handler_name = '_handle_%s' % shape['type']
        elem.tail = True
        if hasattr(self, handler_name):
            return getattr(self, handler_name)(elem, shape)
        else:
            logger.debug('Unhandled type: %s' % shape['type'])

    def fake_shape(self, elem):
        shape = {}
        tags = set()
        nchildren = 0
        for child in elem:
            tags.add(child)
            nchildren += 1
        if nchildren == 0:
            shape['type'] = 'string'
        elif nchildren > 1 and len(tags) == 1:
            shape['type'] = 'list'
            shape['members'] = {'type': 'string'}
        else:
            shape['type'] = 'structure'
            shape['members'] = {}
            for tag in tags:
                base_tag = self.get_element_base_tag(tag)
                shape['members'][base_tag] = {'type': 'string'}
        return shape

    def start(self, elem):
        self.value = {}
        if self.operation.output:
            for member_name in self.operation.output['members']:
                member = self.operation.output['members'][member_name]
                xmlname = member.get('xmlname', member_name)
                child = self.find(elem, xmlname)
                if child is None and member['type'] not in ScalarTypes:
                    child = elem
                if child is not None:
                    self.value[member_name] = self.handle_elem(child, member)
        self.get_response_metadata()
        for child in self.tree:
            if child.tail is not True:
                child_tag = self.get_element_base_tag(child)
                if child_tag not in self.element_map:
                    if not child_tag.startswith(self.operation.name):
                        shape = self.fake_shape(child)
                        self.value[child_tag] = self.handle_elem(child, shape)


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
    logger.debug("Response Body: %s", body)
    if not body:
        return (http_response, body)
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
