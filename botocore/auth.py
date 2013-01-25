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

logger = logging.getLogger(__name__)

try:
    from urllib.parse import quote
    from urllib.parse import urlsplit
except ImportError:
    from urllib import quote
    from urlparse import urlsplit


class SigV2Auth(object):
    """
    Sign a request with Signature V2.
    """
    def __init__(self, credentials, service_name=None, region_name=None):
        self.credentials = credentials
        self.service_name = service_name
        self.region_name = region_name

    def calc_signature(self, args):
        split = urlsplit(args['url'])
        path = split.path
        if len(path) == 0:
            path = '/'
        string_to_sign = '%s\n%s\n%s\n' % (args['method'],
                                           split.netloc,
                                           path)
        lhmac = hmac.new(self.credentials.secret_key.encode('utf-8'),
                        digestmod=sha256)
        args['params']['SignatureMethod'] = 'HmacSHA256'
        if self.credentials.token:
            args['params']['SecurityToken'] = self.credentials.token
        sorted_params = sorted(args['params'])
        pairs = []
        for key in sorted_params:
            value = args['params'][key]
            pairs.append(quote(key, safe='') + '=' +
                         quote(value, safe='-_~'))
        qs = '&'.join(pairs)
        string_to_sign += qs
        logger.debug('string_to_sign')
        logger.debug(string_to_sign)
        lhmac.update(string_to_sign.encode('utf-8'))
        b64 = base64.b64encode(lhmac.digest()).strip().decode('utf-8')
        return (qs, b64)

    def add_auth(self, args):
        args['params']['AWSAccessKeyId'] = self.credentials.access_key
        args['params']['SignatureVersion'] = '2'
        args['params']['Timestamp'] = datetime.datetime.utcnow().isoformat()
        qs, signature = self.calc_signature(args)
        args['params']['Signature'] = signature
        if args['method'] == 'POST':
            args['data'] = args['params']
            args['params'] = {}


PostContentType = 'application/x-www-form-urlencoded; charset=UTF-8'


class SigV4Auth(object):
    """
    Sign a request with Signature V4.
    """

    def __init__(self, credentials, service_name=None, region_name=None):
        self.credentials = credentials
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

    def headers_to_sign(self, args):
        """
        Select the headers from the request that need to be included
        in the StringToSign.
        """
        headers_to_sign = {}
        headers_to_sign = {'Host': self.split.netloc}
        for name, value in args['headers'].items():
            lname = name.lower()
            if lname.startswith('x-amz'):
                headers_to_sign[name] = value
            elif lname == 'content-type':
                headers_to_sign[name] = value
        return headers_to_sign

    def build_payload(self, args):
        """
        For all Query-style requests, we will use POST.

        When using SigV4, we need to convert the query parameters
        to a string and place that in the payload of the POST request.
        """
        if args['method'] == 'POST' and not args['data']:
            parameter_names = sorted(args['params'].keys())
            pairs = []
            for pname in parameter_names:
                pval = str(args['params'][pname]).encode('utf-8')
                pairs.append(quote(pname, safe='') + '=' +
                             quote(pval, safe='-_~'))
            args['data'] = '&'.join(pairs)
            args['params'] = {}
            args['headers']['content-type'] = PostContentType

    def canonical_query_string(self, args):
        cqs = ''
        if args['method'] == 'GET':
            l = []
            for param in args['params']:
                value = str(args['params'][param])
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
        l = ['%s:%s' % (n.lower().strip(),
                      headers_to_sign[n].strip()) for n in headers_to_sign]
        l = sorted(l)
        return '\n'.join(l)

    def signed_headers(self, headers_to_sign):
        l = ['%s' % n.lower().strip() for n in headers_to_sign]
        l = sorted(l)
        return ';'.join(l)

    def payload(self, args):
        if args['data']:
            return sha256(args['data']).hexdigest()
        else:
            return sha256('').hexdigest()

    def canonical_request(self, args):
        cr = [args['method'].upper()]
        path = self.split.path
        if len(path) == 0:
            path = '/'
        cr.append(path)
        cr.append(self.canonical_query_string(args))
        headers_to_sign = self.headers_to_sign(args)
        cr.append(self.canonical_headers(headers_to_sign) + '\n')
        cr.append(self.signed_headers(headers_to_sign))
        cr.append(self.payload(args))
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

    def string_to_sign(self, args, canonical_request):
        """
        Return the canonical StringToSign as well as a dict
        containing the original version of all headers that
        were included in the StringToSign.
        """
        sts = ['AWS4-HMAC-SHA256']
        sts.append(args['headers']['X-Amz-Date'])
        sts.append(self.credential_scope(args))
        sts.append(sha256(canonical_request).hexdigest())
        return '\n'.join(sts)

    def signature(self, args, string_to_sign):
        key = self.credentials.secret_key
        k_date = self._sign(('AWS4' + key).encode('utf-8'),
                            self.timestamp[0:8])
        k_region = self._sign(k_date, self.region_name)
        k_service = self._sign(k_region, self.service_name)
        k_signing = self._sign(k_service, 'aws4_request')
        return self._sign(k_signing, string_to_sign, hex=True)

    def add_auth(self, args):
        # This could be a retry.  Make sure the previous
        # authorization header is removed first.
        self.split = urlsplit(args['url'])
        self.build_payload(args)
        if 'X-Amzn-Authorization' in args['headers']:
            del args['headers']['X-Amzn-Authorization']
        args['headers']['X-Amz-Date'] = self.timestamp
        if self.credentials.token:
            args['headers']['X-Amz-Security-Token'] = self.credentials.token
        canonical_request = self.canonical_request(args)
        logger.debug('CanonicalRequest:\n%s' % canonical_request)
        string_to_sign = self.string_to_sign(args, canonical_request)
        logger.debug('StringToSign:\n%s' % string_to_sign)
        signature = self.signature(args, string_to_sign)
        logger.debug('Signature:\n%s' % signature)
        headers_to_sign = self.headers_to_sign(args)
        l = ['AWS4-HMAC-SHA256 Credential=%s' % self.scope(args)]
        l.append('SignedHeaders=%s' % self.signed_headers(headers_to_sign))
        l.append('Signature=%s' % signature)
        args['headers']['Authorization'] = ','.join(l)


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
        self.service_name = service_name
        self.region_name = region_name

    def sign_string(self, string_to_sign):
        new_hmac = hmac.new(self.credentials.secret_key.encode('utf-8'),
                            digestmod=sha1)
        new_hmac.update(string_to_sign.encode('utf-8'))
        return base64.encodestring(new_hmac.digest()).strip()

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
                    custom_headers[lk] = headers[key].strip()
        sorted_header_keys = sorted(custom_headers.keys())
        hoi = []
        for key in sorted_header_keys:
            hoi.append("%s:%s" % (key, custom_headers[key]))
        return '\n'.join(hoi)

    def canonical_resource(self, path):
        # don't include anything after the first ? in the resource...
        # unless it is one of the QSA of interest, defined above
        buf = ''
        t = path.split('?')
        buf += t[0]

        if len(t) > 1:
            qsa = t[1].split('&')
            qsa = [a.split('=', 1) for a in qsa]
            qsa = [unquote_v(a) for a in qsa if a[0] in self.QSAOfInterest]
            if len(qsa) > 0:
                qsa.sort(cmp=lambda x, y:cmp(x[0], y[0]))
                qsa = ['='.join(a) for a in qsa]
                buf += '?'
                buf += '&'.join(qsa)

        return buf

    def canonical_string(self, method, path, headers, expires=None):
        cs = method.upper() + '\n'
        cs += self.canonical_standard_headers(headers) + '\n'
        custom_headers = self.canonical_custom_headers(headers)
        if custom_headers:
            cs += custom_headers + '\n'
        cs += self.canonical_resource(path)
        return cs

    def get_signature(self, method, path, headers, expires=None):
        if self.credentials.token:
            #TODO: remove hardcoded header name
            headers['security_token'] = self.credentials.token
        string_to_sign = self.canonical_string(method,
                                               path,
                                               headers)
        logger.debug('StringToSign:\n%s' % string_to_sign)
        return self.sign_string(string_to_sign)

    def add_auth(self, args):
        split = urlsplit(args['url'])
        path = split.path
        signature = self.get_signature(args['method'], path,
                                       args['headers'])
        args['headers']['Authorization'] = ("AWS %s:%s" % (self.credentials.access_key,
                                                           signature))


def get_auth(signature_version, *args, **kw):
    if signature_version == 'v2':
        return SigV2Auth(*args, **kw)
    if signature_version == 'v4':
        return SigV4Auth(*args, **kw)
    if signature_version == 's3':
        return HmacV1Auth(*args, **kw)
    raise ValueError('Unknown auth scheme: %s' % auth_name)
