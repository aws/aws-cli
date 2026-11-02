**To retrieve a certificate authority (CA) certificate**

The following ``get-certificate-authority-certificate`` example retrieves the certificate and certificate chain for the private CA specified by the ARN. ::

    aws acm-pca get-certificate-authority-certificate \
        --certificate-authority-arn arn:aws:acm-pca:us-west-2:123456789012:certificate-authority/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --output text

Output::

    -----BEGIN CERTIFICATE-----
    MIIDrzCCApegAwIBAgIRAOskdzLvcj1eShkoyEE693AwDQYJKoZIhvcNAQELBQAw
    cTELMAkGA1UEBhMCVVMxEzARBgNVBAgMCldhc2hpbmd0b24xEDAOBgNVBAcMB1Nl
    kdRGB6P2hpxstDOUIwAoCbhoaWwfA4ybJznf+jOQhAziNlRdKQRR8nODWpKt7H9w
    dJ5nxsTk/fniJz86Ddtp6n8s82wYdkN3cVffeK72A9aTCOU=
    -----END CERTIFICATE----- -----BEGIN CERTIFICATE-----
    MIIDxjCCAq6gAwIBAgIQCv2jEXAMPLEi8l1pBwUNKjANBgkqhkiG9w0BAQsFADBx
    MQswCQYDVQQGEwJVUzETMBEGA1UECAwKV2FzaGluZ3RvbjEQMA4GA1UEBwwHU2Vh
    dHRsZTEVMBMGA1UECgwMRXhhbXBsZSBDb3JwMQ4wDAYDVQQLDAVTYWxlczEUMBIG
    A1UEAwwLZXhhbXBsZS5jb20=
    -----END CERTIFICATE-----

For more information, see `Installing the CA certificate <https://docs.aws.amazon.com/privateca/latest/userguide/PCACertInstall.html>`__ in the *AWS Private Certificate Authority User Guide*.
