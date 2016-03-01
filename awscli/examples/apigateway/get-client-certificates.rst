**To get the per-region list of client certificates**

Command::

  aws apigateway get-client-certificates --region us-west-2

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

