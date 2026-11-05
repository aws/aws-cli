**To import a certificate into ACM.**

The following ``import-certificate`` example imports a certificate into ACM. Replace the file names with your own. ::

    aws acm import-certificate \
        --certificate file://Certificate.pem \
        --certificate-chain file://CertificateChain.pem \
        --private-key file://PrivateKey.pem

Contents of ``Certificate.pem``::

    -----BEGIN CERTIFICATE-----
    EXAMPLECERTIFICATEDATA...
    -----END CERTIFICATE-----

Contents of ``CertificateChain.pem``::

    -----BEGIN CERTIFICATE-----
    EXAMPLEINTERMEDIATECERTIFICATEDATA...
    -----END CERTIFICATE-----
    -----BEGIN CERTIFICATE-----
    EXAMPLEROOTCERTIFICATEDATA...
    -----END CERTIFICATE-----

Contents of ``PrivateKey.pem``::

    -----BEGIN PRIVATE KEY-----
    EXAMPLEPRIVATEKEYDATA...
    -----END PRIVATE KEY-----

Output::

    {
        "CertificateArn": "arn:aws:acm:us-west-2:123456789012:certificate/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Import certificates into AWS Certificate Manager <https://docs.aws.amazon.com/acm/latest/userguide/import-certificate.html>`__ in the *AWS Certificate Manager User Guide*.
