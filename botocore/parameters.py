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
import decimal

import six
import dateutil.parser

from botocore import BotoCoreObject
from botocore.exceptions import ValidationError, RangeError, UnknownKeyError
from botocore.exceptions import MissingParametersError


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
        self.example_fn = None
        BotoCoreObject.__init__(self, **kwargs)
        self.cli_name = '--' + self.cli_name
        self._handle_subtypes()

    def _handle_subtypes(self):
        # Subclasses can implement this method to handle
        # any members they might have (useful for complex types).
        pass

    def validate(self, value):
        """Validate the value.

        If a parameter decides the value is not a valid value
        then they can raise a ``ValidationError``.

        """
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
        elif style == 'rest-json' or style == 'rest-xml':
            payload = built_params.get('payload')
            if payload is not None:
                payload.add_param(self, value, label)

    def build_parameter(self, style, value, built_params, label=''):
        self.validate(value)
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
                                 param=self,
                                 min_value=self.min,
                                 max_value=self.max)
        if self.max:
            if value > self.max:
                raise RangeError(value=value,
                                 param=self,
                                 min_value=self.min,
                                 max_value=self.max)
        return value


class FloatParameter(Parameter):

    def validate(self, value):
        original_value = value
        # So isinstance(True, int) -> True.
        # For a float parameter we should not allow a bool.
        if isinstance(value, bool):
            raise ValidationError(value=str(value), type_name='float',
                                  param=self)
        elif not isinstance(value, float):
            # If the value is a float, that's good enough for a float
            # param.  Also you can't go directly from a float -> Decimal
            # in python2.6.
            # Otherwise the value has to look like a decimal,
            # so we just need to validate that it converts to a
            # decimal without issue and then run it through the min
            # max range validations.
            try:
                # We don't want to type convert here, but we need
                # to convert it to something we can use < and > against.
                value = decimal.Decimal(value)
            except (decimal.InvalidOperation, TypeError):
                raise ValidationError(value=str(value), type_name='float',
                                      param=self)
        if self.min:
            if value < self.min:
                raise RangeError(value=value,
                                 param=self,
                                 min_value=self.min,
                                 max_value=self.max)
        if self.max:
            if value > self.max:
                raise RangeError(value=value,
                                 param=self,
                                 min_value=self.min,
                                 max_value=self.max)
        return original_value


class DoubleParameter(Parameter):

    def validate(self, value):
        if not isinstance(value, float):
            raise ValidationError(value=str(value), type_name='double',
                                  param=self)
        if self.min:
            if value < self.min:
                raise RangeError(value=value,
                                 param=self,
                                 min_value=self.min,
                                 max_value=self.max)
        if self.max:
            if value > self.max:
                raise RangeError(value=value,
                                 param=self,
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

    def _getstring(self, value):
        if value:
            value = 'true'
        else:
            value = 'false'
        return value

    def build_parameter_query(self, value, built_params, label=''):
        value = self.validate(value)
        value = self._getstring(value)
        self.store_value_query(value, built_params, label)

    @property
    def false_name(self):
        false_name = ''
        if self.required:
            false_name = '--no-' + self.cli_name[2:]
        return false_name

    def to_xml(self, value, label=None):
        if not label:
            label = self.name
        value = self._getstring(value)
        return '<%s>%s</%s>' % (label, value, label)


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
                                 param=self,
                                 min_value=self.min,
                                 max_value=self.max)
        if self.max:
            if len(value) > self.max:
                raise RangeError(value=len(value),
                                 param=self,
                                 min_value=self.min,
                                 max_value=self.max)
        return value


class BlobParameter(Parameter):

    def validate(self, value):
        allowed_types = six.string_types + (bytes, bytearray,)
        if self.payload and self.streaming:
            # Streaming blobs should be file-like objects or be strings.
            if not hasattr(value, 'read') and not isinstance(value, allowed_types):
                raise ValidationError(value=str(value), type_name='blob',
                                      param=self)
        else:
            if not isinstance(value, allowed_types):
                raise ValidationError(value=str(value), type_name='string',
                                      param=self)
            if not hasattr(self, 'payload') or self.payload is False:
                # Blobs that are not in the payload should be base64-encoded
                value = base64.b64encode(six.b(value)).decode('utf-8')
        return value


class ListParameter(Parameter):

    def validate(self, value):
        if not isinstance(value, (list, tuple)):
            raise ValidationError(value=value, type_name='list', param=self)
        for item in value:
            try:
                self.members.validate(item)
            except ValidationError as e:
                # ValidationError must provide a value
                # argument so we can safely access that key.
                raise ValidationError(value=e.kwargs['value'],
                                      param='element of %s' % self,
                                      type_name='list')
        return value

    def _handle_subtypes(self):
        if self.members:
            self.members = get_parameter(self.operation, None, self.members)

    def build_parameter_query(self, value, built_params, label=''):
        logger.debug("Building parameter for query service, name: %r, "
                     "label: %r", self.get_label(), label)
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
            xmlname = self.xmlname
            if not xmlname:
                xmlname = self.members.xmlname
            inner_xml += self.members.to_xml(item, xmlname)
        if self.flattened:
            return inner_xml
        else:
            if not label:
                label = self.xmlname
            return '<%s>' % label + inner_xml + '</%s>' % label


class MapParameter(Parameter):

    def validate(self, value):
        if not isinstance(value, dict):
            raise ValidationError(value=str(value),
                                  type_name='map', param=self)

    def _handle_subtypes(self):
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
            member_type.build_parameter_query(
                value[v], built_params,
                '%s.%d.%s' % (label, i, member_type.xmlname))

    def build_parameter_json(self, value, built_params, label=''):
        label = self.get_label()
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
        self._validate_known_keys(value)
        self._validate_required_keys(value)
        for member in self.members:
            sub_value = value.get(member.name)
            if sub_value is not None:
                member.validate(sub_value)

    def _validate_known_keys(self, value):
        valid_keys = [p.name for p in self.members]
        for key in value:
            if key not in valid_keys:
                raise UnknownKeyError(
                    value=key, choices=', '.join(valid_keys), param=self.name)

    def _validate_required_keys(self, value):
        # There are some inner params that are marked as required
        # even though the parent param is not marked required.
        # It would be a good enhancement to also validate those
        # params.
        missing = []
        for required in [p.name for p in self.members if p.required]:
            if required not in value:
                missing.append(required)
        if missing:
            raise MissingParametersError(object_name=self,
                                         missing=', '.join(missing))

    def _handle_subtypes(self):
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
            if member.required and member.name not in value:
                msg = 'Expected: %s, Got: %s' % (member.name, value.keys())
                raise ValueError(msg)
            if member.name in value:
                member.build_parameter_query(value[member.name],
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
            if member.required and member.name not in value:
                msg = 'Expected: %s, Got: %s' % (member.name, value.keys())
                raise ValueError(msg)
            if member.name in value:
                member_label = member.get_label()
                member.build_parameter_json(value[member.name],
                                            new_value,
                                            member_label)

    def store_value_json(self, value, built_params, label):
        label = self.get_label()
        built_params[label] = {}
        for member in self.members:
            if member.name in value:
                member.store_value_json(value[member.name],
                                        built_params[label],
                                        member.name)

    def to_xml(self, value, label=None):
        if not label:
            label = self.get_label()
        xml = '<%s' % label
        if hasattr(self, 'xmlnamespace'):
            xml += ' xmlns:%s="%s" ' % (self.xmlnamespace['prefix'],
                                       self.xmlnamespace['uri'])
            # Now we need to look for members that have an
            # xmlattribute attribute with a value of True.
            # The value of these attributes belongs in the xmlattribute
            # not in the body of the element.
            for member in self.members:
                if hasattr(member, 'xmlattribute'):
                    xml += '%s="%s"' % (member.xmlname, value[member.name])
        xml += '>'
        for member in self.members:
            if member.name in value and not hasattr(member, 'xmlattribute'):
                xml += member.to_xml(value[member.name], member.name)
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
