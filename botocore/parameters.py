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
import logging
import base64
import datetime
import time
import six
import dateutil.parser
from . import BotoCoreObject
from .exceptions import ValidationError, RangeError

logger = logging.getLogger(__name__)


class Parameter(BotoCoreObject):

    def __init__(self, operation, **kwargs):
        self.operation = operation
        self.xmlname = None
        self.required = False
        self.flattened = False
        self.allow_file = False
        self.min = None
        self.max = None
        self.payload = False
        self.streaming = False
        BotoCoreObject.__init__(self, **kwargs)
        self.cli_name = '--' + self.cli_name
        self.handle_subtypes()

    def handle_subtypes(self):
        pass

    def validate(self, value):
        pass

    def get_label(self):
        if self.xmlname:
            label = self.xmlname
        else:
            label = self.name
        return label

    def store_value_query(self, value, built_params, label):
        if label:
            label = label.format(label=self.get_label())
        else:
            label = self.get_label()
        built_params[label] = str(value)

    def build_parameter_query(self, value, built_params, label=''):
        value = self.validate(value)
        self.store_value_query(value, built_params, label)

    def store_value_json(self, value, built_params, label):
        if isinstance(built_params, list):
            built_params.append(value)
        else:
            label = self.get_label()
            built_params[label] = value

    def build_parameter_json(self, value, built_params, label=''):
        value = self.validate(value)
        self.store_value_json(value, built_params, value)

    def build_parameter_rest(self, style, value, built_params, label=''):
        if hasattr(self, 'location'):
            if self.location == 'uri':
                built_params['uri_params'][self.name] = value
            elif self.location == 'header':
                if hasattr(self, 'location_name'):
                    key = self.location_name
                else:
                    key = self.name
                built_params['headers'][key] = value
        elif style == 'rest-json':
            logger.debug('JSON Payload found')
            if built_params['payload'] is None:
                built_params['payload'] = {}
            self.store_value_json(value, built_params['payload'], label)
        elif style == 'rest-xml' and not self.streaming:
            logger.debug('XML Payload found')
            xml_payload = self.to_xml(value)
            logger.debug(xml_payload)
            built_params['payload'] = xml_payload
        else:
            built_params['payload'] = value

    def build_parameter(self, style, value, built_params, label=''):
        if style == 'query':
            self.build_parameter_query(value, built_params, label)
        elif style == 'json':
            self.build_parameter_json(value, built_params, label)
        elif style in ('rest-xml', 'rest-json'):
            self.build_parameter_rest(style, value, built_params, label)

    def to_xml(self, value, label=None):
        if not label:
            label = self.name
        return '<%s>%s</%s>' % (label, value, label)


class IntegerParameter(Parameter):

    def validate(self, value):
        if not isinstance(value, six.integer_types):
            raise ValidationError(value=str(value), type_name='integer',
                                  param=self)
        if self.min:
            if value < self.min:
                raise RangeError(value=value,
                                 min_value=self.min,
                                 max_value=self.max)
        if self.max:
            if value > self.max:
                raise RangeError(value=value,
                                 min_value=self.min,
                                 max_value=self.max)
        return value


class FloatParameter(Parameter):

    def validate(self, value):
        if not isinstance(value, float):
            raise ValidationError(value=str(value), type_name='float',
                                  param=self)
        if self.min:
            if value < self.min:
                raise RangeError(value=value,
                                 min_value=self.min,
                                 max_value=self.max)
        if self.max:
            if value > self.max:
                raise RangeError(value=value,
                                 min_value=self.min,
                                 max_value=self.max)
        return value


class DoubleParameter(Parameter):

    def validate(self, value):
        if not isinstance(value, double):
            raise ValidationError(value=str(value), type_name='double',
                                   param=self)
        if self.min:
            if value < self.min:
                raise RangeError(value=value,
                                 min_value=self.min,
                                 max_value=self.max)
        if self.max:
            if value > self.max:
                raise RangeError(value=value,
                                 min_value=self.min,
                                 max_value=self.max)
        return value


class BooleanParameter(Parameter):

    def validate(self, value):
        try:
            if not isinstance(value, bool):
                if isinstance(value, six.string_types):
                    if value.lower() == 'true':
                        value = True
                    elif value.lower() == 'false':
                        value = False
                    else:
                        raise ValueError
            return value
        except ValueError:
            raise ValidationError(value=str(value), type_name='boolean',
                                  param=self)

    def build_parameter_query(self, value, built_params, label=''):
        value = self.validate(value)
        if value:
            value = 'true'
        else:
            value = 'false'
        self.store_value_query(value, built_params, label)

    @property
    def false_name(self):
        false_name = ''
        if self.required:
            false_name = '--no-' + self.cli_name[2:]
        return false_name


class TimestampParameter(Parameter):

    Epoch = datetime.datetime(1970, 1, 1)

    def totalseconds(self, td):
        value = td.microseconds + (td.seconds + td.days * 24 * 3600)
        return value * 10**6 / 10**6

    def validate(self, value):
        try:
            return dateutil.parser.parse(value)
        except:
            pass
        try:
            # Might be specified as an epoch time
            return datetime.datetime.utcfromtimestamp(value)
        except:
            pass
        raise ValidationError(value=str(value), type_name='timestamp',
                              param=self)

    def get_time_value(self, value):
        if self.operation.service.timestamp_format == 'unixTimestamp':
            delta = value - self.Epoch
            value = int(self.totalseconds(delta))
        else:
            value = value.isoformat()
        return value

    def build_parameter_query(self, value, built_params, label=''):
        value = self.validate(value)
        self.store_value_query(self.get_time_value(value),
                               built_params, label)

    def build_parameter_json(self, value, built_params, label=''):
        value = self.validate(value)
        self.store_value_json(self.get_time_value(value), built_params, value)


class StringParameter(Parameter):

    def validate(self, value):
        if not isinstance(value, six.string_types):
            raise ValidationError(value=str(value), type_name='string',
                                  param=self)

        if self.min:
            if len(value) < self.min:
                raise RangeError(value=len(value),
                                 min_value=self.min,
                                 max_value=self.max)
        if self.max:
            if len(value) > self.max:
                raise RangeError(value=len(value),
                                 min_value=self.min,
                                 max_value=self.max)
        return value


class BlobParameter(Parameter):

    def validate(self, value):
        if self.payload and self.streaming:
            # Streaming blobs should be file-like objects
            if not hasattr(value, 'read'):
                raise ValidationError(value=str(value), type_name='blob',
                                      param=self)
        else:
            if not isinstance(value, six.string_types):
                raise ValidationError(value=str(value), type_name='string',
                                      param=self)
            if not hasattr(self, 'payload') or self.payload is False:
                # Blobs that are not in the payload should be base64-encoded
                value = base64.b64encode(six.b(value)).decode('utf-8')
        return value


class ListParameter(Parameter):

    def validate(self, value):
        if not isinstance(value, (list, tuple)):
            value = [value]
        return value

    def handle_subtypes(self):
        if self.members:
            self.members = get_parameter(self.operation, None, self.members)

    def build_parameter_query(self, value, built_params, label=''):
        logger.debug('name: %s' % self.get_label())
        logger.debug('label: %s' % label)
        value = self.validate(value)
        # If this is not a flattened list, find the label for member
        # items in the list.
        member_type = self.members
        if self.flattened:
            if member_type.xmlname:
                if label:
                    label = label.format(label=member_type.xmlname)
                else:
                    label = member_type.xmlname
            else:
                if label:
                    label = label.format(label=self.get_label())
                else:
                    label = self.get_label()
        else:
            if label:
                label = label.format(label=self.get_label())
            else:
                label = self.get_label()
            label = '%s.%s' % (label, 'member')
        for i, v in enumerate(value, 1):
            member_type.build_parameter_query(v, built_params,
                                              '%s.%d' % (label, i))

    def build_parameter_json(self, value, built_params, label=''):
        value = self.validate(value)
        label = self.get_label()
        built_params[label] = []
        for v in value:
            self.members.build_parameter_json(v, built_params[label], None)

    def to_xml(self, value, label=None):
        inner_xml = ''
        for item in value:
            inner_xml += self.members.to_xml(item, self.xmlname)
        if self.flattened:
            return inner_xml
        else:
            if not label:
                label = self.xmlname
            return '<%s>' % label  + inner_xml + '</%s>' % label


class MapParameter(Parameter):

    def validate(self, value):
        if not isinstance(value, dict):
            raise ValidationError(value=str(value), type_name='map', param=self)

    def handle_subtypes(self):
        if self.members:
            self.members = get_parameter(self.operation, None, self.members)
        if self.keys:
            self.keys = get_parameter(self.operation, None, self.keys)

    def build_parameter_query(self, value, built_params, label=''):
        label = self.get_label()
        key_type = self.keys
        member_type = self.members
        for i, v in enumerate(value, 1):
            built_params['%s.%d.%s' % (label, i, key_type.xmlname)] = v
            member_type.build_parameter_query(value[v], built_params,
                                              '%s.%d.%s' % (label, i, member_type.xmlname))

    def build_parameter_json(self, value, built_params, label=''):
        label = self.get_label()
        key_type = self.keys
        member_type = self.members
        new_value = {}
        if isinstance(built_params, list):
            built_params.append(new_value)
        else:
            built_params[label] = new_value
        for key in value:
            new_value[key] = value[key]


class StructParameter(Parameter):

    def validate(self, value):
        if not isinstance(value, dict):
            raise ValidationError(value=str(value), type_name='structure',
                                  param=self)

    def handle_subtypes(self):
        if self.members:
            l = []
            for name, data in self.members.items():
                l.append(get_parameter(self.operation, name, data))
            self.members = l

    def build_parameter_query(self, value, built_params, label=''):
        if label:
            label = label.format(label=self.get_label())
        else:
            label = self.get_label()
        label = '%s.{label}' % label
        for member in self.members:
            if member.required and member.py_name not in value:
                msg = 'Expected: %s, Got: %s' % (member.py_name, value.keys())
                raise ValueError(msg)
            if member.py_name in value:
                member.build_parameter_query(value[member.py_name],
                                             built_params,
                                             label)

    def build_parameter_json(self, value, built_params, label=''):
        label = self.get_label()
        new_value = {}
        if isinstance(built_params, list):
            built_params.append(new_value)
        else:
            built_params[label] = new_value
        for member in self.members:
            if member.required and member.py_name not in value:
                msg = 'Expected: %s, Got: %s' % (member.py_name, value.keys())
                raise ValueError(msg)
            if member.py_name in value:
                member_label = member.get_label()
                member.build_parameter_json(value[member.py_name],
                                            new_value,
                                            member_label)

    def store_value_json(self, value, built_params, label):
        label = self.get_label()
        built_params[label] = {}
        for member in self.members:
            if member.py_name in value:
                member.store_value_json(value[member.py_name],
                                        built_params[label],
                                        member.name)

    def to_xml(self, value, label=None):
        if not label:
            label = self.get_label()
        xml = '<%s>' % label
        for member in self.members:
            if member.py_name in value:
                xml += member.to_xml(value[member.py_name], member.name)
        xml += '</%s>' % label
        return xml

type_map = {
    'structure': StructParameter,
    'map': MapParameter,
    'timestamp': TimestampParameter,
    'list': ListParameter,
    'string': StringParameter,
    'blob': BlobParameter,
    'float': FloatParameter,
    'double': DoubleParameter,
    'integer': IntegerParameter,
    'long': IntegerParameter,
    'boolean': BooleanParameter,
    'double': FloatParameter,
    'member': Parameter,
    'file': StringParameter}


def get_parameter(operation, name, type_data):
    """
    Returns a Parameter object based on the parameter data passed in.
    """
    if name and 'name' not in type_data:
        type_data['name'] = name
    param_cls = type_map[type_data['type']]
    obj = param_cls(operation, **type_data)
    return obj
