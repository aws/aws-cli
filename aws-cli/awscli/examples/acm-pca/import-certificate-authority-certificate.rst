**To import your certificate authority certificate into ACM PCA**

The following ``import-certificate-authority-certificate`` example imports the signed private CA certificate for the CA specified by the ARN into ACM PCA. ::

    aws acm-pca import-certificate-authority-certificate \
        --certificate-authority-arn arn:aws:acm-pca:us-west-2:123456789012:certificate-authority/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --certificate fileb://C:\ca_cert.pem \
        --certificate-chain fileb://C:\ca_cert_chain.pem

This command produces no output.

For more information, see `Installing the CA certificate <https://docs.aws.amazon.com/privateca/latest/userguide/PCACertInstall.html>`__ in the *AWS Private Certificate Authority User Guide*.
