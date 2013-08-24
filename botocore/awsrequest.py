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
from requests import models

from botocore.compat import HTTPHeaders


class AWSRequest(models.RequestEncodingMixin, models.Request):
    def __init__(self, *args, **kwargs):
        self.auth_path = None
        if 'auth_path' in kwargs:
            self.auth_path = kwargs['auth_path']
            del kwargs['auth_path']
        models.Request.__init__(self, *args, **kwargs)
        headers = HTTPHeaders()
        if self.headers is not None:
            for key, value in self.headers.items():
                headers[key] = value
        self.headers = headers

    def prepare(self):
        """Constructs a :class:`AWSPreparedRequest <AWSPreparedRequest>`."""
        # Eventually I think it would be nice to add hooks into this process.
        p = AWSPreparedRequest(self)
        p.prepare_method(self.method)
        p.prepare_url(self.url, self.params)
        p.prepare_headers(self.headers)
        p.prepare_cookies(self.cookies)
        p.prepare_body(self.data, self.files)
        p.prepare_auth(self.auth)
        return p

    @property
    def body(self):
        p = models.PreparedRequest()
        p.prepare_headers({})
        p.prepare_body(self.data, self.files)
        return p.body


class AWSPreparedRequest(models.PreparedRequest):
    """Represents a prepared request.

    :ivar method: HTTP Method
    :ivar url: The full url
    :ivar headers: The HTTP headers to send.
    :ivar body: The HTTP body.
    :ivar hooks: The set of callback hooks.

    In addition to the above attributes, the following attributes are
    available:

    :ivar query_params: The original query parameters.
    :ivar post_param: The original POST params (dict).

    """
    def __init__(self, original_request):
        self.original = original_request
        super(AWSPreparedRequest, self).__init__()
