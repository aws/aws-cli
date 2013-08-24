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
Payloads
--------
These payload objects are used to manage the payload (e.g. body) of
PUT and POST requests.  These bodies are either:

* JSON documents that accumulate the values of 1 or more parameters.
  In this situation, the values are accumulated in a Python dict and
  then marshalled to a JSON string.
* XML documents that accumulate the values of 1 or more parameters.
  In this case, the xml fragments are accumulated and a complete
  XML document is assembled as a string.
* Literal values such as raw strings or file-like objects that need
  to be copied into the request body.
"""
import logging
from botocore.compat import json


logger = logging.getLogger(__name__)


class Payload(object):

    def __init__(self):
        self._literal_value = None

    @property
    def literal_value(self):
        return self._literal_value

    @literal_value.setter
    def literal_value(self, literal_value):
        self._literal_value = literal_value

    def add_param(self, param, value, label=None):
        """
        Add a parameter to this JSON payload.
        """
        self._literal_value = value

    def getvalue(self):
        return self._literal_value


class JSONPayload(Payload):
    """
    A JSON payload.

    The parameters are added to the payload one at a time and the
    complete JSON body is returned as a string by the ``getvalue``
    method.
    """

    def __init__(self):
        super(JSONPayload, self).__init__()
        self._value = {}

    def add_param(self, param, value, label=None):
        """
        Add a parameter to this JSON payload.
        """
        param.store_value_json(value, self._value, label)

    def getvalue(self):
        """
        Return the value of the payload as a JSON string.
        """
        value = self._literal_value
        if self._value:
            value = json.dumps(self._value)
        return value


class XMLPayload(Payload):
    """
    XML Payload.

    One or more parameters may be added to this payload and the
    complete XML body is constructed and returned as a string by
    the ``getvalue`` method.

    There are two types of XML payloads encountered.

    In the case of S3 and CloudFront requests, one (and only one)
    parameter of an operation can have a ``payload=true`` attribute.
    In this case, the value of that single parameter is the complete
    body of the XML payload.

    In the case of Route53 requests, the entire input is treated as
    the XML payload.  It will have one or more members whose values
    must be added to the final XML document.  In addition, the input
    may have other parameters that need to be added to the URI or to
    a header and these parameters are not added to the payload.

    To distinquish between these two types, we use two factors:

    * ``root_element_name`` attribute.  Route53 payloads have a
      ``root_element_name`` attribute but S3 payloads do not.
    * A ``payload=True`` attribute.  Route53 payloads do not have
      this attribute but S3 and CloudFront do.

    I'm not sure if this is the best way to discriminate between the
    two types but it seems effective.

    Alternatively, the ``literal_value`` property can be set and this
    value will be returned as-is by the ``getvalue`` method.
    """

    def __init__(self, root_element_name, namespace=None):
        super(XMLPayload, self).__init__()
        self.root_element_name = root_element_name
        self.namespace = namespace
        self._elements = []
        self._payload = False

    def add_param(self, param, value, label=None):
        if hasattr(param, 'payload') and param.payload:
            self._payload = True
        self._elements.append(param.to_xml(value, label))

    def _assemble_xml(self):
        s = '<%s' % self.root_element_name
        if self.namespace:
            s += ' xmlns="%s"' % self.namespace
        s += '>'
        for element in self._elements:
            s += element
        s += '</%s>' % self.root_element_name
        logger.debug('assembled XML: %s', s)
        return s

    def getvalue(self):
        value = self._literal_value
        if len(self._elements) > 0:
            if self.root_element_name and not self._payload:
                value = self._assemble_xml()
            else:
                value = self._elements[0]
        return value
