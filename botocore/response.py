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
from .hooks import first_non_none_response
from botocore.compat import json
import logging

logger = logging.getLogger(__name__)


class Response(object):

    def __init__(self, session, operation):
        self.session = session
        self.operation = operation
        self.value = {}

    def parse(self, s, encoding):
        pass

    def get_value(self):
        value = ''
        if self.value:
            value = self.value
        return value

    def merge_header_values(self, headers):
        pass


class XmlResponse(Response):

    def __init__(self, session, operation):
        Response.__init__(self, session, operation)
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

    def parse(self, s, encoding):
        parser = xml.etree.cElementTree.XMLParser(
            target=xml.etree.cElementTree.TreeBuilder(),
            encoding=encoding)
        parser.feed(s)
        self.tree = parser.close()
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
            if request_id is None:
                request_id = self.tree.find(self.clark_notation('RequestId'))
            if request_id is None:
                request_id = self.tree.find('RequestID')
        if request_id is not None:
            request_id.tail = True
            rmd['RequestId'] = request_id.text.strip()

    def _get_error_data(self, error_elem):
        data = {}
        for elem in error_elem:
            elem.tail = True
            data[self.get_element_base_tag(elem)] = elem.text
        return data

    def get_response_errors(self):
        errors = None
        error_elems = self.tree.find('Errors')
        if error_elems is not None:
            error_elems.tail = True
            errors = [self._get_error_data(e) for e in error_elems]
        else:
            error_elems = self.tree.find(self.clark_notation('Error'))
            if error_elems is not None:
                error_elems.tail = True
                errors = [self._get_error_data(error_elems)]
            elif self.tree.tag == 'Error':
                errors = [self._get_error_data(self.tree)]
        if errors:
            self.value['Errors'] = errors

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
    _handle_blob = _handle_string

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
                new_data[member_name] = self.handle_elem(member_name, child,
                                                         member_shape)
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
        return [self.handle_elem(None, child, shape['members'])
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
            key_name = self.handle_elem(None, key, keyshape)
            data[key_name] = self.handle_elem(key_name, value, valueshape)
        return data

    def emit_event(self, tag, shape, value):
        if 'shape_name' in shape:
            event = self.session.create_event(
                'after-parsed', self.operation.service.endpoint_prefix,
                self.operation.name, shape['shape_name'], tag)
            rv = first_non_none_response(self.session.emit(event,
                                                           shape=shape,
                                                           value=value),
                                         None)
            if rv:
                value = rv
        return value

    def handle_elem(self, key, elem, shape):
        handler_name = '_handle_%s' % shape['type']
        elem.tail = True
        if hasattr(self, handler_name):
            value = getattr(self, handler_name)(elem, shape)
            value = self.emit_event(key, shape, value)
            return value
        else:
            logger.debug('Unhandled type: %s', shape['type'])

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
                    self.value[member_name] = self.handle_elem(member_name,
                                                               child, member)
        self.get_response_metadata()
        self.get_response_errors()
        for child in self.tree:
            if child.tail is not True:
                child_tag = self.get_element_base_tag(child)
                if child_tag not in self.element_map:
                    if not child_tag.startswith(self.operation.name):
                        shape = self.fake_shape(child)
                        self.value[child_tag] = self.handle_elem(child_tag,
                                                                 child, shape)

    def merge_header_values(self, headers):
        if self.operation.output:
            for member_name in self.operation.output['members']:
                member = self.operation.output['members'][member_name]
                location = member.get('location')
                if location == 'header':
                    location_name = member.get('location_name')
                    if location_name in headers:
                        self.value[member_name] = headers[location_name]


class JSONResponse(Response):

    def parse(self, s, encoding):
        try:
            decoded = s.decode(encoding)
            self.value = json.loads(decoded)
            self.get_response_errors()
        except Exception as err:
            logger.debug('Error loading JSON response body, %r', err)

    def get_response_errors(self):
        # Most JSON services return a __type in error response bodies.
        # Unfortunately, ElasticTranscoder does not.  It simply returns
        # a JSON body with a single key, "message".
        error = None
        if '__type' in self.value:
            error_type = self.value['__type']
            error = {'Type': error_type}
            del self.value['__type']
            if 'message' in self.value:
                error['Message'] = self.value['message']
                del self.value['message']
            code = self._parse_code_from_type(error_type)
            error['Code'] = code
        elif 'message' in self.value and len(self.value.keys()) == 1:
            error = {'Type': 'Unspecified', 'Code': 'Unspecified',
                     'Message': self.value['message']}
            del self.value['message']
        if error:
            self.value['Errors'] = [error]

    def _parse_code_from_type(self, error_type):
        return error_type.rsplit('#', 1)[-1]


class StreamingResponse(Response):

    def __init__(self, session, operation):
        Response.__init__(self, session, operation)
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


def get_response(session, operation, http_response):
    encoding = 'utf-8'
    if http_response.encoding:
        encoding = http_response.encoding
    content_type = http_response.headers['content-type']
    if content_type and ';' in content_type:
        content_type = content_type.split(';')[0]
        logger.debug('Content type from response: %s', content_type)
    if operation.is_streaming():
        streaming_response = StreamingResponse(session, operation)
        streaming_response.parse(http_response.headers, http_response.raw)
        return (http_response, streaming_response.get_value())
    body = http_response.content
    logger.debug("Response Body:\n%s", body)
    if content_type in ('application/x-amz-json-1.0',
                        'application/x-amz-json-1.1', 'application/json'):
        json_response = JSONResponse(session, operation)
        if body:
            json_response.parse(body, encoding)
        json_response.merge_header_values(http_response.headers)
        return (http_response, json_response.get_value())
    # We are defaulting to an XML response handler because many query
    # services send XML error responses but do not include a Content-Type
    # header.
    xml_response = XmlResponse(session, operation)
    if body:
        xml_response.parse(body, encoding)
    xml_response.merge_header_values(http_response.headers)
    return (http_response, xml_response.get_value())
