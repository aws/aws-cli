**To delete a private certificate authority**

The following ``delete-certificate-authority`` example deletes the certificate authority identified by the ARN. ::

    aws acm-pca delete-certificate-authority \
        --certificate-authority-arn arn:aws:acm-pca:us-west-2:123456789012:certificate-authority/12345678-1234-1234-1234-123456789012

This command produces no output.

For more information, see `Delete your private CA <https://docs.aws.amazon.com/privateca/latest/userguide/PCADeleteCA.html>`__ in the *AWS Private Certificate Authority User Guide*.
