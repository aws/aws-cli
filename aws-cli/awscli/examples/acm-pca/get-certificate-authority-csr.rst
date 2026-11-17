**To retrieve the certificate signing request for a certificate authority**

The following ``get-certificate-authority-csr`` example retrieves the CSR for the private CA specified by the ARN. ::

    aws acm-pca get-certificate-authority-csr \
        --certificate-authority-arn arn:aws:acm-pca:us-west-2:123456789012:certificate-authority/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --output text

Output::

    -----BEGIN CERTIFICATE REQUEST-----
    MIICvjCCAaYCAQAweTELMAkGA1UEBhMCVVMxEzARBgNVBAgMCldhc2hpbmd0b24x
    EDAOBgNVBAcMB1NlYXR0bGUxFTATBgNVBAoMDEV4YW1wbGUgQ29ycDEOMAwGA1UE
    CwwFU2FsZXMxGDAWBgNVBAMMD3d3dy5leGFtcGxlLmNvbTCCASIwDQYJKoZIhvcN
    AQEBBQADggEPADCCAQoCggEBAMEXAMPLEKEYBODYPLACEHOLDERVALUE0000000=
    -----END CERTIFICATE REQUEST-----

For more information, see `Installing the CA certificate <https://docs.aws.amazon.com/privateca/latest/userguide/PCACertInstall.html>`__ in the *AWS Private Certificate Authority User Guide*.
