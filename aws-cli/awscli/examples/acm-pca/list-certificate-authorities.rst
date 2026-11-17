**To list your private certificate authorities**

The following ``list-certificate-authorities`` example lists information about all of the private CAs in your account. ::

    aws acm-pca list-certificate-authorities \
        --max-results 10

Output::

    {
        "CertificateAuthorities": [
            {
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
        ]
    }

For more information, see `List private CAs <https://docs.aws.amazon.com/privateca/latest/userguide/list-CAs.html>`__ in the *AWS Private Certificate Authority User Guide*.
