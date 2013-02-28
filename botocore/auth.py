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
import base64
import datetime
from hashlib import sha256
from hashlib import sha1
import hmac
import logging
from email.utils import formatdate
from botocore.exceptions import UnknownSignatureVersionError
from botocore.exceptions import NoCredentialsError
from botocore.utils import normalize_url_path
from botocore.compat import HTTPHeaders
from six.moves import http_client

logger = logging.getLogger(__name__)

try:
    from urllib.parse import quote
    from urllib.parse import unquote
    from urllib.parse import urlsplit
    from urllib.parse import parse_qsl
except ImportError:
    from urllib import quote
    from urllib import unquote
    from urlparse import urlsplit
    from urlparse import parse_qsl


PostContentType = 'application/x-www-form-urlencoded; charset=UTF-8'
EMPTY_SHA256_HASH = (
    'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')


class SigV2Auth(object):
    """
    Sign a request with Signature V2.
    """
    def __init__(self, credentials, service_name=None, region_name=None):
        self.credentials = credentials
        if self.credentials is None:
            raise NoCredentialsError
        self.service_name = service_name
        self.region_name = region_name

    def calc_signature(self, request, params):
        split = urlsplit(request.url)
        path = split.path
        if len(path) == 0:
            path = '/'
        string_to_sign = '%s\n%s\n%s\n' % (request.method,
                                           split.netloc,
                                           path)
        lhmac = hmac.new(self.credentials.secret_key.encode('utf-8'),
                         digestmod=sha256)
        pairs = []
        for key in sorted(params):
            value = params[key]
            pairs.append(quote(key, safe='') + '=' +
                         quote(value, safe='-_~'))
        qs = '&'.join(pairs)
        string_to_sign += qs
        logger.debug('string_to_sign')
        logger.debug(string_to_sign)
        lhmac.update(string_to_sign.encode('utf-8'))
        b64 = base64.b64encode(lhmac.digest()).strip().decode('utf-8')
        return (qs, b64)

    def add_auth(self, request):
        # The auth handler is the last thing called in the
        # preparation phase of a prepared request.
        # Because of this we have to parse the query params
        # from the request body so we can update them with
        # the sigv2 auth params.
        if request.data:
            # POST
            params = request.data
        else:
            # GET
            params = request.param
        params['AWSAccessKeyId'] = self.credentials.access_key
        params['SignatureVersion'] = '2'
        params['SignatureMethod'] = 'HmacSHA256'
        params['Timestamp'] = datetime.datetime.utcnow().isoformat()
        if self.credentials.token:
            params['SecurityToken'] = self.credentials.token
        qs, signature = self.calc_signature(request, params)
        params['Signature'] = signature
        return request


class SigV3Auth(object):
    def __init__(self, credentials, service_name=None, region_name=None):
        self.credentials = credentials
        if self.credentials is None:
            raise NoCredentialsError
        self.service_name = service_name
        self.region_name = region_name

    def add_auth(self, request):
        if 'Date' not in request.headers:
            request.headers['Date'] = formatdate(usegmt=True)
        if self.credentials.token:
            request.headers['X-Amz-Security-Token'] = self.credentials.token
        new_hmac = hmac.new(self.credentials.secret_key.encode('utf-8'),
                            digestmod=sha256)
        new_hmac.update(request.headers['Date'].encode('utf-8'))
        encoded_signature = base64.encodestring(new_hmac.digest()).strip()
        signature = ('AWS3-HTTPS AWSAccessKeyId=%s,Algorithm=%s,Signature=%s' %
                     (self.credentials.access_key, 'HmacSHA256',
                      encoded_signature.decode('utf-8')))
        request.headers['X-Amzn-Authorization'] = signature


class SigV4Auth(object):
    """
    Sign a request with Signature V4.
    """

    def __init__(self, credentials, service_name=None, region_name=None):
        self.credentials = credentials
        if self.credentials is None:
            raise NoCredentialsError
        self.now = datetime.datetime.utcnow()
        self.timestamp = self.now.strftime('%Y%m%dT%H%M%SZ')
        self.region_name = region_name
        self.service_name = service_name

    def _sign(self, key, msg, hex=False):
        if hex:
            sig = hmac.new(key, msg.encode('utf-8'), sha256).hexdigest()
        else:
            sig = hmac.new(key, msg.encode('utf-8'), sha256).digest()
        return sig

    def headers_to_sign(self, request):
        """
        Select the headers from the request that need to be included
        in the StringToSign.
        """
        header_map = HTTPHeaders()
        split = urlsplit(request.url)
        for name, value in request.headers.items():
            lname = name.lower()
            header_map[lname] = value
        if 'host' not in header_map:
            header_map['host'] = split.netloc
        return header_map

    def canonical_query_string(self, request):
        cqs = ''
        if request.params:
            params = request.params
            l = []
            for param in params:
                value = str(params[param])
                l.append('%s=%s' % (quote(param, safe='-_.~'),
                                    quote(value, safe='-_.~')))
            l = sorted(l)
            cqs = '&'.join(l)
        return cqs

    def canonical_headers(self, headers_to_sign):
        """
        Return the headers that need to be included in the StringToSign
        in their canonical form by converting all header keys to lower
        case, sorting them in alphabetical order and then joining
        them into a string, separated by newlines.
        """
        headers = []
        for key in set(headers_to_sign):
            value = ','.join(v.strip() for v in
                            sorted(headers_to_sign.get_all(key)))
            headers.append('%s:%s' % (key, value))
        headers.sort()
        return '\n'.join(headers)

    def signed_headers(self, headers_to_sign):
        l = ['%s' % n.lower().strip() for n in set(headers_to_sign)]
        l = sorted(l)
        return ';'.join(l)

    def payload(self, request):
        if request.body:
            return sha256(request.body.encode('utf-8')).hexdigest()
        else:
            return EMPTY_SHA256_HASH

    def canonical_request(self, request):
        cr = [request.method.upper()]
        path = normalize_url_path(urlsplit(request.url).path)
        cr.append(path)
        cr.append(self.canonical_query_string(request))
        headers_to_sign = self.headers_to_sign(request)
        cr.append(self.canonical_headers(headers_to_sign) + '\n')
        cr.append(self.signed_headers(headers_to_sign))
        cr.append(self.payload(request))
        return '\n'.join(cr)

    def scope(self, args):
        scope = [self.credentials.access_key]
        scope.append(self.timestamp[0:8])
        scope.append(self.region_name)
        scope.append(self.service_name)
        scope.append('aws4_request')
        return '/'.join(scope)

    def credential_scope(self, args):
        scope = []
        scope.append(self.timestamp[0:8])
        scope.append(self.region_name)
        scope.append(self.service_name)
        scope.append('aws4_request')
        return '/'.join(scope)

    def string_to_sign(self, request, canonical_request):
        """
        Return the canonical StringToSign as well as a dict
        containing the original version of all headers that
        were included in the StringToSign.
        """
        sts = ['AWS4-HMAC-SHA256']
        sts.append(self.timestamp)
        sts.append(self.credential_scope(request))
        sts.append(sha256(canonical_request.encode('utf-8')).hexdigest())
        return '\n'.join(sts)

    def signature(self, string_to_sign):
        key = self.credentials.secret_key
        k_date = self._sign(('AWS4' + key).encode('utf-8'),
                            self.timestamp[0:8])
        k_region = self._sign(k_date, self.region_name)
        k_service = self._sign(k_region, self.service_name)
        k_signing = self._sign(k_service, 'aws4_request')
        return self._sign(k_signing, string_to_sign, hex=True)

    def add_auth(self, request):
        # This could be a retry.  Make sure the previous
        # authorization header is removed first.
        split = urlsplit(request.url)
        if 'Authorization' in request.headers:
            del request.headers['Authorization']
        if 'Date' not in request.headers:
            request.headers['X-Amz-Date'] = self.timestamp
        if self.credentials.token:
            request.headers['X-Amz-Security-Token'] = self.credentials.token
        canonical_request = self.canonical_request(request)
        logger.debug('CanonicalRequest:\n%s' % canonical_request)
        string_to_sign = self.string_to_sign(request, canonical_request)
        logger.debug('StringToSign:\n%s' % string_to_sign)
        signature = self.signature(string_to_sign)
        logger.debug('Signature:\n%s' % signature)
        l = ['AWS4-HMAC-SHA256 Credential=%s' % self.scope(request)]
        headers_to_sign = self.headers_to_sign(request)
        l.append('SignedHeaders=%s' % self.signed_headers(headers_to_sign))
        l.append('Signature=%s' % signature)
        request.headers['Authorization'] = ', '.join(l)
        return request


class HmacV1Auth(object):

    # List of Query String Arguments of Interest
    QSAOfInterest = ['acl', 'cors', 'defaultObjectAcl', 'location', 'logging',
                     'partNumber', 'policy', 'requestPayment', 'torrent',
                     'versioning', 'versionId', 'versions', 'website',
                     'uploads', 'uploadId', 'response-content-type',
                     'response-content-language', 'response-expires',
                     'response-cache-control', 'response-content-disposition',
                     'response-content-encoding', 'delete', 'lifecycle',
                     'tagging', 'restore', 'storageClass']

    def __init__(self, credentials, service_name=None, region_name=None):
        self.credentials = credentials
        if self.credentials is None:
            raise NoCredentialsError
        self.service_name = service_name
        self.region_name = region_name

    def sign_string(self, string_to_sign):
        new_hmac = hmac.new(self.credentials.secret_key.encode('utf-8'),
                            digestmod=sha1)
        new_hmac.update(string_to_sign.encode('utf-8'))
        return base64.encodestring(new_hmac.digest()).strip().decode('utf-8')

    def canonical_standard_headers(self, headers):
        interesting_headers = ['content-md5', 'content-type', 'date']
        hoi = []
        if 'Date' not in headers:
            headers['Date'] = formatdate(usegmt=True)
        for ih in interesting_headers:
            found = False
            for key in headers:
                lk = key.lower()
                if headers[key] != None and lk == ih:
                    hoi.append(headers[key].strip())
                    found = True
            if not found:
                hoi.append('')
        return '\n'.join(hoi)

    def canonical_custom_headers(self, headers):
        custom_headers = {}
        for key in headers:
            lk = key.lower()
            if headers[key] != None:
                # TODO: move hardcoded prefix to provider
                if lk.startswith('x-amz-'):
                    custom_headers[lk] = ','.join(v.strip() for v in
                                                   headers.get_all(key))
        sorted_header_keys = sorted(custom_headers.keys())
        hoi = []
        for key in sorted_header_keys:
            hoi.append("%s:%s" % (key, custom_headers[key]))
        return '\n'.join(hoi)

    def unquote_v(self, nv):
        """
        TODO: Do we need this?
        """
        if len(nv) == 1:
            return nv
        else:
            return (nv[0], unquote(nv[1]))

    def canonical_resource(self, split):
        # don't include anything after the first ? in the resource...
        # unless it is one of the QSA of interest, defined above
        buf = split.path

        if split.query:
            qsa = split.query.split('&')
            qsa = [a.split('=', 1) for a in qsa]
            qsa = [self.unquote_v(a) for a in qsa if a[0] in self.QSAOfInterest]
            if len(qsa) > 0:
                qsa.sort(cmp=lambda x, y:cmp(x[0], y[0]))
                qsa = ['='.join(a) for a in qsa]
                buf += '?'
                buf += '&'.join(qsa)

        return buf

    def canonical_string(self, method, split, headers, expires=None):
        cs = method.upper() + '\n'
        cs += self.canonical_standard_headers(headers) + '\n'
        custom_headers = self.canonical_custom_headers(headers)
        if custom_headers:
            cs += custom_headers + '\n'
        cs += self.canonical_resource(split)
        return cs

    def get_signature(self, method, split, headers, expires=None):
        if self.credentials.token:
            #TODO: remove hardcoded header name
            headers['security_token'] = self.credentials.token
        string_to_sign = self.canonical_string(method,
                                               split,
                                               headers)
        logger.debug('StringToSign:\n%s' % string_to_sign)
        return self.sign_string(string_to_sign)

    def add_auth(self, request):
        split = urlsplit(request.url)
        logger.debug('Method: %s' % request.method)
        signature = self.get_signature(request.method, split,
                                       request.headers)
        request.headers['Authorization'] = ("AWS %s:%s" % (self.credentials.access_key,
                                                           signature))


def get_auth(signature_version, *args, **kw):
    if signature_version == 'v2':
        return SigV2Auth(*args, **kw)
    elif signature_version == 'v4':
        return SigV4Auth(*args, **kw)
    elif signature_version == 's3':
        return HmacV1Auth(*args, **kw)
    elif signature_version == 'v3':
        return SigV3Auth(*args, **kw)
    raise UnknownSignatureVersionError(signature_version=signature_version)
