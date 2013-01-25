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
import six
import dateutil.parser
from . import BotoCoreObject
from .exceptions import ValidationError, RangeError

logger = logging.getLogger(__name__)


class Parameter(BotoCoreObject):

    def __init__(self, **kwargs):
        self.xmlname = None
        self.required = False
        self.flattened = False
        self.min = None
        self.max = None
        BotoCoreObject.__init__(self, **kwargs)
        self.cli_name = '--' + self.cli_name
        # if not self.xmlname:
        #     self.xmlname = self.name
        self.handle_subtypes()

    def handle_subtypes(self):
        pass

    def validate(self, value):
        pass

    def get_label(self, label=None):
        if not label:
            if self.xmlname:
                label = self.xmlname
            else:
                label = self.name
        return label

    def build_parameter_query(self, value, built_params,
                              label='', flattened=False):
        logger.debug('label=%s' % label)
        value = self.validate(value)
        label = self.get_label(label)
        built_params[label] = str(value)

    def build_parameter_json(self, value, built_params,
                             label=''):
        value = self.validate(value)
        if isinstance(built_params, list):
            built_params.append(value)
        else:
            label = self.get_label(label)
            built_params[label] = value

    def build_parameter_rest(self, value, built_params,
                             label=''):
        logger.debug('value=%s' % value)
        logger.debug(built_params)
        logger.debug(label)
        logger.debug(self.location)
        if self.location == 'uri':
            built_params['uri_params'][self.name] = value
        elif self.location == 'header':
            built_params['headers'][self.name] = value

    def build_parameter(self, style, value, built_params, label=''):
        if style == 'query':
            self.build_parameter_query(value, built_params, label)
        elif style == 'json':
            self.build_parameter_json(value, built_params, label)
        elif style == 'rest-xml':
            self.build_parameter_rest(value, built_params, label)


class IntegerParameter(Parameter):

    def validate(self, value):
        if not isinstance(value, six.integer_types):
            raise ValidationError(value=str(value), type_name='integer')
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
            raise ValidationError(value=str(value), type_name='float')
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
            raise ValidationError(value=str(value), type_name='boolean')

    def build_parameter_query(self, value, built_params,
                              label='', flattened=False):
        value = self.validate(value)
        if value:
            value = 'true'
        else:
            value = 'false'
        label = self.get_label(label)
        built_params[label] = value

    def build_parameter_json(self, value, built_params, label=''):
        value = self.validate(value)
        if value:
            value = True
        else:
            value = False
        if isinstance(built_params, list):
            built_params.append(value)
        else:
            label = self.get_label(label)
            built_params[label] = value


class TimestampParameter(Parameter):

    def validate(self, value):
        try:
            dt = dateutil.parser.parse(value)
            return dt.isoformat()
        except ValueError:
            raise ValidationError(value=str(value),
                                  type_name='timestamp')


class StringParameter(Parameter):

    def validate(self, value):
        if not isinstance(value, six.string_types):
            raise ValidationError(value=str(value), type_name='string')

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


class ListParameter(Parameter):

    def validate(self, value):
        if not isinstance(value, (list, tuple)):
            value = [value]
        return value

    def handle_subtypes(self):
        if self.members:
            self.members = get_parameter(None, self.members)

    def build_parameter_query(self, value, built_params,
                              label='', flattened=False):
        value = self.validate(value)
        label = self.get_label(label)
        member_type = self.members
        # If this is not a flattened list, find the label for member
        # items in the list.
        if self.flattened or flattened:
            if not self.xmlname:
                label = member_type.get_label()
        else:
            if member_type.xmlname:
                member_name = member_type.xmlname
            else:
                member_name = 'member'
            label = '%s.%s' % (self.name, member_name)
        for i, v in enumerate(value, 1):
            member_type.build_parameter_query(v, built_params,
                                              '%s.%d' % (label, i),
                                              self.flattened or flattened)

    def build_parameter_json(self, value, built_params, label=''):
        value = self.validate(value)
        label = self.get_label(label)
        member_type = self.members
        if self.flattened:
            label = member_type.xmlname
        else:
            if member_type.xmlname:
                member_name = member_type.xmlname
            else:
                member_name = 'member'
            label = '%s.%s' % (self.name, member_name)
        built_params[label] = []
        for i, v in enumerate(value, 1):
            member_type.build_parameter_json(v, built_params[label], None)


class MapParameter(Parameter):

    def validate(self, value):
        if not isinstance(value, dict):
            raise ValidationError(value=str(value), type_name='map')

    def handle_subtypes(self):
        if self.members:
            self.members = get_parameter(None, self.members)
        if self.keys:
            self.keys = get_parameter(None, self.keys)

    def build_parameter_query(self, value, built_params,
                              label='', flattened=False):
        logger.debug(value)
        logger.debug('label=%s' % label)
        logger.debug('flattened=%s' % flattened)
        label = self.get_label(label)
        key_type = self.keys
        member_type = self.members
        for i, v in enumerate(value, 1):
            built_params['%s.%d.%s' % (label, i, key_type.xmlname)] = v
            member_type.build_parameter_query(value[v], built_params,
                                              '%s.%d.%s' % (label, i, member_type.xmlname),
                                              flattened)

    def build_parameter_json(self, value, built_params, label=''):
        if not isinstance(value, (list, tuple)):
            value = [value]
        label = self.get_label(label)
        member_type = self.members
        for i, v in enumerate(value, 1):
            member_type.build_parameter_json(v, built_params,
                                             '%s.%d' % (label, i))


class StructParameter(Parameter):

    def validate(self, value):
        if not isinstance(value, dict):
            raise ValidationError(value=str(value), type_name='structure')

    def handle_subtypes(self):
        if self.members:
            l = []
            for name, data in self.members.items():
                l.append(get_parameter(name, data))
            self.members = l

    def build_parameter_query(self, value, built_params,
                              label='', flattened=False):
        label = self.get_label(label)
        logger.debug('label=%s' % label)
        for member in self.members:
            if member.required and member.py_name not in value:
                msg = 'Expected: %s, Got: %s' % (member.py_name, value.keys())
                raise ValueError(msg)
            if member.py_name in value:
                member_label = member.get_label()
                member.build_parameter_query(value[member.py_name],
                                             built_params,
                                             label + '.' + member_label,
                                             flattened)

    def build_parameter_json(self, value, built_params, label=''):
        label = self.get_label(label)
        built_params[label] = value
        for member in self.members:
            if member.required and member.py_name not in value:
                msg = 'Expected: %s, Got: %s' % (member.py_name, value.keys())
                raise ValueError(msg)
            if member.py_name in value:
                member_label = member.get_label()
                member.build_parameter_json(value[member.py_name],
                                            built_params[label],
                                            member_label)

type_map = {
    'structure': StructParameter,
    'map': MapParameter,
    'timestamp': TimestampParameter,
    'list': ListParameter,
    'string': StringParameter,
    'blob': StringParameter,
    'float': FloatParameter,
    'integer': IntegerParameter,
    'long': IntegerParameter,
    'boolean': BooleanParameter,
    'double': FloatParameter,
    'member': Parameter,
    'jsondoc': StringParameter,
    'file': StringParameter}


def get_parameter(name, type_data):
    """
    Returns a Parameter object based on the parameter data passed in.
    """
    if name and 'name' not in type_data:
        type_data['name'] = name
    param_cls = type_map[type_data['type']]
    obj = param_cls(**type_data)
    return obj
