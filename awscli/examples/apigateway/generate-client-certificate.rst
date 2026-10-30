**To create a Client-Side SSL Certificate**

The following ``generate-client-certificate`` example creates a client-side SSL certificate. ::

    aws apigateway generate-client-certificate \
        --description 'My First Client Certificate'

Output::

    {
        "clientCertificateId": "a1b2c3",
        "description": "My First Client Certificate",
        "pemEncodedCertificate": "-----BEGIN CERTIFICATE-----\nMIIC6TCCAdGgAwIBAgIJAKbyiCf2f5J2MA0GCSqGSIb3DQEBCwUAMDQxCzAJBgNVEXAMPLE\n-----END CERTIFICATE-----\n",
        "createdDate": "2016-02-23T23:39:00+00:00",
        "expirationDate": "2017-02-23T23:39:00+00:00",
        "tags": {}
    }
