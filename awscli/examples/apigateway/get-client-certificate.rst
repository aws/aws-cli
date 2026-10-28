**To get a client certificate**

The following ``get-client-certificate`` example gets the client certificate with the ID ``a1b2c3``. ::

    aws apigateway get-client-certificate \
        --client-certificate-id a1b2c3

Output::

    {
        "clientCertificateId": "a1b2c3",
        "description": "My First Client Certificate",
        "pemEncodedCertificate": "-----BEGIN CERTIFICATE-----\nMIIC6TCCAdGgAwIBAgIJAKbyiCf2f5J2MA0GCSqGSIb3DQEBCwUAMDQxCzAJBgNVEXAMPLE\n-----END CERTIFICATE-----\n",
        "createdDate": "2016-02-23T23:39:00+00:00",
        "expirationDate": "2017-02-23T23:39:00+00:00",
        "tags": {}
    }
