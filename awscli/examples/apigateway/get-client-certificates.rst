**To get a list of client certificates**

The following ``get-client-certificates`` example gets a list of client certificates. ::

    aws apigateway get-client-certificates

Output::

    {
        "items": [
            {
                "pemEncodedCertificate": "-----BEGIN CERTIFICATE----- <certificate content> -----END CERTIFICATE-----",
                "clientCertificateId": "a1b2c3",
                "expirationDate": 1483556561,
                "description": "My Client Certificate",
                "createdDate": 1452020561
            }
        ]
    }

