from requests import models
from requests.structures import CaseInsensitiveDict

from botocore.compat import HTTPHeaders


class AWSRequest(models.RequestEncodingMixin, models.Request):
    def __init__(self, *args, **kwargs):
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
