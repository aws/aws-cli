**To remove one or more tags from your private certificate authority**

The following ``untag-certificate-authority`` example removes tags from the private CA identified by the ARN. ::

    aws acm-pca untag-certificate-authority \
        --certificate-authority-arn arn:aws:acm-pca:us-west-2:123456789012:certificate-authority/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --tags Key=Purpose,Value=Website

This command produces no output.

For more information, see `Add tags for your private CA <https://docs.aws.amazon.com/privateca/latest/userguide/PcaCaTagging.html>`__ in the *AWS Private Certificate Authority User Guide*.
