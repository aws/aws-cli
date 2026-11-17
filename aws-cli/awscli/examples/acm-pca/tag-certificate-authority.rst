**To attach tags to a private certificate authority**

The following ``tag-certificate-authority`` example attaches one or more tags to your private CA. ::

    aws acm-pca tag-certificate-authority \
        --certificate-authority-arn arn:aws:acm-pca:us-west-2:123456789012:certificate-authority/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --tags Key=Admin,Value=Alice

This command produces no output.

For more information, see `Add tags for your private CA <https://docs.aws.amazon.com/privateca/latest/userguide/PcaCaTagging.html>`__ in the *AWS Private Certificate Authority User Guide*.
