**To describe a private certificate authority**

The following ``describe-certificate-authority`` example lists information about the private CA identified by the ARN. ::

    aws acm-pca describe-certificate-authority \
        --certificate-authority-arn arn:aws:acm-pca:us-west-2:123456789012:certificate-authority/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "CertificateAuthority": {
            "Arn": "arn:aws:acm-pca:us-west-2:123456789012:certificate-authority/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "OwnerAccount": "123456789012",
            "CreatedAt": "2023-08-21T20:30:15.123000+00:00",
            "LastStateChangeAt": "2023-08-21T20:45:47.456000+00:00",
            "Type": "SUBORDINATE",
            "Serial": "4109",
            "Status": "ACTIVE",
            "NotBefore": "2023-08-21T19:45:47+00:00",
            "NotAfter": "2033-08-21T20:45:47+00:00",
            "CertificateAuthorityConfiguration": {
                "KeyAlgorithm": "RSA_2048",
                "SigningAlgorithm": "SHA256WITHRSA",
                "Subject": {
                    "Country": "US",
                    "Organization": "Example Corp",
                    "OrganizationalUnit": "Sales",
                    "State": "WA",
                    "CommonName": "www.example.com",
                    "Locality": "Seattle"
                }
            },
            "RevocationConfiguration": {
                "CrlConfiguration": {
                    "Enabled": true,
                    "ExpirationInDays": 7,
                    "CustomCname": "crl.example.com",
                    "S3BucketName": "amzn-s3-demo-bucket",
                    "S3ObjectAcl": "BUCKET_OWNER_FULL_CONTROL"
                },
                "OcspConfiguration": {
                    "Enabled": false
                }
            },
            "KeyStorageSecurityStandard": "FIPS_140_2_LEVEL_3_OR_HIGHER",
            "UsageMode": "GENERAL_PURPOSE"
        }
    }

For more information, see `View a private CA <https://docs.aws.amazon.com/privateca/latest/userguide/describe-CA.html>`__ in the *AWS Private Certificate Authority User Guide*.
