**To retrieve an issued certificate**

The following ``get-certificate`` example retrieves a certificate from the specified private CA. ::

    aws acm-pca get-certificate \
        --certificate-authority-arn arn:aws:acm-pca:us-west-2:123456789012:certificate-authority/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --certificate-arn arn:aws:acm-pca:us-west-2:123456789012:certificate-authority/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/certificate/6707447683a9b7f4055627ffd55cebcc \
        --output text

Output::

    -----BEGIN CERTIFICATE-----
    MIIEDzCCAvegAwIBAgIRAJuJ8f6ZVYL7gG/rS3qvrZMwDQYJKoZIhvcNAQELBQAw
    cTELMAkGA1UEBhMCVVMxEzARBgNVBAgMCldhc2hpbmd0b24xEDAOBgNVBAcMB1Nl
        ....certificate body truncated for brevity....
    tKCSglgZZrd4FdLw1EkGm+UVXnodwMtJEQyy3oTfZjURPIyyaqskTu/KSS7YDjK0
    KQNy73D6LtmdOEbAyq10XiDxqY41lvKHJ1eZrPaBmYNABxU=
    -----END CERTIFICATE---- -----BEGIN CERTIFICATE-----
    MIIDrzCCApegAwIBAgIRAOskdzLvcj1eShkoyEE693AwDQYJKoZIhvcNAQELBQAw
    cTELMAkGA1UEBhMCVVMxEzARBgNVBAgMCldhc2hpbmd0b24xEDAOBgNVBAcMB1Nl
        ...certificate body truncated for brevity....
    kdRGB6P2hpxstDOUIwAoCbhoaWwfA4ybJznf+jOQhAziNlRdKQRR8nODWpKt7H9w
    dJ5nxsTk/fniJz86Ddtp6n8s82wYdkN3cVffeK72A9aTCOU=
    -----END CERTIFICATE-----

The first part of the output is the certificate itself. The second part is the certificate chain that chains to the root CA certificate. Note that when you use the ``--output text`` option, a ``TAB`` character is inserted between the two certificate pieces (that is the cause of the indented text). If you intend to take this output and parse the certificates with other tools, you might need to remove the ``TAB`` character so it is processed correctly.

For more information, see `Retrieve a private certificate <https://docs.aws.amazon.com/privateca/latest/userguide/PcaGetCert.html>`__ in the *AWS Private Certificate Authority User Guide*.
