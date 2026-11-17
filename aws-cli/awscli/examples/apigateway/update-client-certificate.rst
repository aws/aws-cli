**To update the description of a client certificate**

The following ``update-client-certificate`` example updates the description of a client certificate. ::

    aws apigateway update-client-certificate \
        --client-certificate-id a1b2c3 \
        --patch-operations op='replace',path='/description',value='My new description'

Output::

    {
        "clientCertificateId": "a1b2c3",
        "description": "My new description",
        "pemEncodedCertificate": "-----BEGIN CERTIFICATE-----\nMIIC6TCCAdGgAwIBAgIJAKbyiCf2f5J2MA0GCSqGSIb3DQEBCwUAMDQxCzAJBgNVEXAMPLE\n-----END CERTIFICATE-----\n",
        "createdDate": "2016-02-23T23:39:00+00:00",
        "expirationDate": "2017-02-23T23:39:00+00:00",
        "tags": {}
    }

For more information, see `Use an API Gateway-generated certificate for backend authentication in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/getting-started-client-side-ssl-authentication.html>`__ in the *Amazon API Gateway Developer Guide*.
