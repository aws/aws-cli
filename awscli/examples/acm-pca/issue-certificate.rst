**To issue a private certificate**

The following ``issue-certificate`` example uses the private CA specified by the ARN to issue a private certificate. ::

    aws acm-pca issue-certificate \
        --certificate-authority-arn arn:aws:acm-pca:us-west-2:123456789012:certificate-authority/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --csr fileb://C:\cert_1.csr \
        --signing-algorithm "SHA256WITHRSA" \
        --validity Value=365,Type="DAYS" \
        --idempotency-token 1234

Output::

    {
        "CertificateArn": "arn:aws:acm-pca:us-west-2:123456789012:certificate-authority/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/certificate/6707447683a9b7f4055627ffd55cebcc"
    }

For more information, see `Issue private end-entity certificates <https://docs.aws.amazon.com/privateca/latest/userguide/PcaIssueCert.html>`__ in the *AWS Private Certificate Authority User Guide*.
