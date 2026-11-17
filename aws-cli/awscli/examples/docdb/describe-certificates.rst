**To list the available CA certificates**

The following ``describe-certificates`` example lists the certificate authority (CA) certificates that Amazon DocumentDB provides for TLS connections in the current AWS Region. ::

    aws docdb describe-certificates

Output::

    {
        "Certificates": [
            {
                "CertificateIdentifier": "rds-ca-ecc384-g1",
                "CertificateType": "CA",
                "Thumbprint": "24a97b91cbe86911190576c35c36aab4fa7b25de",
                "ValidFrom": "2021-05-25T22:41:55+00:00",
                "ValidTill": "2121-05-25T23:41:55+00:00",
                "CertificateArn": "arn:aws:rds:us-west-2::cert:rds-ca-ecc384-g1"
            },
            {
                "CertificateIdentifier": "rds-ca-rsa4096-g1",
                "CertificateType": "CA",
                "Thumbprint": "9da6fa7fd2ec09c569a400d876b01b0c12759a96",
                "ValidFrom": "2021-05-25T22:38:35+00:00",
                "ValidTill": "2121-05-25T23:38:35+00:00",
                "CertificateArn": "arn:aws:rds:us-west-2::cert:rds-ca-rsa4096-g1"
            },
            {
                "CertificateIdentifier": "rds-ca-rsa2048-g1",
                "CertificateType": "CA",
                "Thumbprint": "2fa77ef894d983ba9d37ad699c84ab0f657be1c8",
                "ValidFrom": "2021-05-25T22:34:57+00:00",
                "ValidTill": "2061-05-25T23:34:57+00:00",
                "CertificateArn": "arn:aws:rds:us-west-2::cert:rds-ca-rsa2048-g1"
            }
        ]
    }

For more information, see `Updating your Amazon DocumentDB TLS certificates <https://docs.aws.amazon.com/documentdb/latest/devguide/ca_cert_rotation.html>`__ in the *Amazon DocumentDB Developer Guide*.
