**To register a self signed device certificate**

The following ``register-certificate`` example registers the ``deviceCert.pem`` device certificate signed by the ``rootCA.pem`` CA certificate. The CA certificate must be registered before you use it to register a self-signed device certificate. The self-signed certificate must be signed by the same CA certificate you pass to this command. ::

    aws iot register-certificate \
        --certificate-pem file://deviceCert.pem \
        --ca-certificate-pem file://rootCA.pem

Contents of ``deviceCert.pem``::

    -----BEGIN CERTIFICATE-----
    MIIDWTCCAkGgAwIBAgIUEXAMPLEEXAMPLEEXAMPLEEXAMPLEEXAMPLEwDQYJKoZI
    hvcNAQELBQAwTDELMAkGA1UEBhMCVVMxEzARBgNVBAgMCldhc2hpbmd0b24xEDAO
    ...
    EXAMPLEEXAMPLEEXAMPLEEXAMPLEEXAMPLEEXAMPLEEXAMPLEEXAMPLE==
    -----END CERTIFICATE-----

Contents of ``rootCA.pem``::

    -----BEGIN CERTIFICATE-----
    MIIDWTCCAkGgAwIBAgIUEXAMPLEEXAMPLEEXAMPLEEXAMPLEEXAMPLEwDQYJKoZI
    hvcNAQELBQAwTDELMAkGA1UEBhMCVVMxEzARBgNVBAgMCldhc2hpbmd0b24xEDAO
    ...
    EXAMPLEEXAMPLEEXAMPLEEXAMPLEEXAMPLEEXAMPLEEXAMPLEEXAMPLE==
    -----END CERTIFICATE-----

Output::

    {
        "certificateArn": "arn:aws:iot:us-west-2:123456789012:cert/488b6a7f2acdeb00a77384e63c4e40b18b1b3caaae57b7272ba44c45e3448142",
        "certificateId": "488b6a7f2acdeb00a77384e63c4e40b18b1b3caaae57b7272ba44c45e3448142"
    }

For more information, see `Register a client certificate manually <https://docs.aws.amazon.com/iot/latest/developerguide/manual-cert-registration.html>`__ in the *AWS IoT Core Developer Guide*.
