**To create a private certificate authority**

The following ``create-certificate-authority`` example creates a private certificate authority in your AWS account. ::

    aws acm-pca create-certificate-authority \
        --certificate-authority-configuration file://C:\ca_config.txt \
        --revocation-configuration file://C:\revoke_config.txt \
        --certificate-authority-type "SUBORDINATE" \
        --idempotency-token 98256344

Contents of ``C:\ca_config.txt``::

    {
        "KeyAlgorithm": "RSA_2048",
        "SigningAlgorithm": "SHA256WITHRSA",
        "Subject": {
            "Country": "US",
            "Organization": "Example Corp",
            "OrganizationalUnit": "Sales",
            "State": "WA",
            "Locality": "Seattle",
            "CommonName": "www.example.com"
        }
    }

Contents of ``C:\revoke_config.txt``::

    {
        "CrlConfiguration": {
            "Enabled": true,
            "ExpirationInDays": 7,
            "CustomCname": "crl.example.com",
            "S3BucketName": "amzn-s3-demo-bucket"
        }
    }


Output::

    {
        "CertificateAuthorityArn": "arn:aws:acm-pca:us-west-2:123456789012:certificate-authority/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Create a private CA in AWS Private CA <https://docs.aws.amazon.com/privateca/latest/userguide/create-CA.html>`__ in the *AWS Private Certificate Authority User Guide*.
