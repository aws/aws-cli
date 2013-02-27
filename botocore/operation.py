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
from .parameters import get_parameter
from .exceptions import MissingParametersError
from .paginate import Paginator
from . import BotoCoreObject

logger = logging.getLogger(__name__)


class Operation(BotoCoreObject):

    _DEFAULT_PAGINATOR_CLS = Paginator

    def __init__(self, service, op_data, paginator_cls=None):
        self.input = {}
        self.output = {}
        BotoCoreObject.__init__(self, **op_data)
        self.service = service
        self.type = 'operation'
        self._get_parameters()
        if paginator_cls is None:
            paginator_cls = self._DEFAULT_PAGINATOR_CLS
        self._paginator_cls = paginator_cls

    def __repr__(self):
        return 'Operation:%s' % self.name

    def call(self, endpoint, **kwargs):
        logger.debug(kwargs)
        params = self.build_parameters(**kwargs)
        return endpoint.make_request(self, params)

    @property
    def can_paginate(self):
        return hasattr(self, 'pagination')

    def paginate(self, endpoint, **kwargs):
        """Iterate over the responses of an operation.

        This will return an iterator with each element
        being a tuple of (``http_response``, ``parsed_response``).
        If the operation does not paginate, a ``TypeError`` will
        be raised.  You can check if an operation can be paginated
        by using the ``can_paginate`` arg.
        """
        if not self.can_paginate:
            raise TypeError("Operation cannot be paginated: %s" % self)
        paginator = self._paginator_cls(self)
        return paginator.paginate(endpoint, **kwargs)

    def _get_parameters(self):
        """
        Build the list of Parameter objects for this operation.
        """
        self.params = []
        if self.input and 'members' in self.input:
            for name, data in self.input['members'].items():
                param = get_parameter(name, data)
                self.params.append(param)

    def _get_built_params(self):
        d = {}
        if self.service.type in ('rest-xml', 'rest-json'):
            d['uri_params'] = {}
            d['headers'] = {}
            d['payload'] = None
        return d

    def build_parameters(self, **kwargs):
        """
        Returns a dictionary containing the kwargs for the
        given operation formatted as required to pass to the service
        in a request.
        """
        logger.debug(kwargs)
        built_params = self._get_built_params()
        missing = []
        for param in self.params:
            if param.required:
                missing.append(param)
            if param.py_name in kwargs:
                if missing:
                    missing.pop()
                param.build_parameter(self.service.type,
                                      kwargs[param.py_name],
                                      built_params)
        if missing:
            missing_str = ','.join([p.py_name for p in missing])
            raise MissingParametersError(missing=missing_str)
        return built_params

    def is_streaming(self):
        is_streaming = False
        if self.output:
            for member_name in self.output['members']:
                member_dict = self.output['members'][member_name]
                if member_dict['type'] == 'blob':
                    if member_dict.get('payload', False):
                        if member_dict.get('streaming', False):
                            is_streaming = True
        return is_streaming
