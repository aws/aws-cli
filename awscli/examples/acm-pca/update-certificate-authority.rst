**To update the configuration of your private certificate authority**

The following ``update-certificate-authority`` example updates the status and configuration of the private CA identified by the ARN. ::

    aws acm-pca update-certificate-authority \
        --certificate-authority-arn arn:aws:acm-pca:us-west-2:123456789012:certificate-authority/12345678-1234-1234-1234-1232456789012 \
        --revocation-configuration file://C:\revoke_config.txt \
        --status "DISABLED"

Contents of ``C:\revoke_config.txt``::

    {
        "CrlConfiguration": {
            "Enabled": true,
            "ExpirationInDays": 7,
            "CustomCname": "crl.example.com",
            "S3BucketName": "amzn-s3-demo-bucket"
        }
    }

This command produces no output.

For more information, see `Update a private CA in AWS Private Certificate Authority <https://docs.aws.amazon.com/privateca/latest/userguide/PCAUpdateCA.html>`__ in the *AWS Private Certificate Authority User Guide*.
