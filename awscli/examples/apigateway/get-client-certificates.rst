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

For more information, see `Use an API Gateway-generated certificate for backend authentication in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/getting-started-client-side-ssl-authentication.html>`__ in the *Amazon API Gateway Developer Guide*.
