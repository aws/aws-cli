**To export a private certificate issued by a private CA.**

The following ``export-certificate`` example exports a private certificate, certificate chain, and private key to your display. ::

    aws acm export-certificate \
        --certificate-arn arn:aws:acm:region:account:certificate/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --passphrase file://path-to-passphrase-file

Contents of ``path-to-passphrase-file``::

    examplePassphrase123

Output::

    {
        "Certificate": "-----BEGIN CERTIFICATE-----\nMIICiTCCAfICCQD6m7oRw0uXOjANBgkqhkiG9w0BAQUFADCBiDELMAkGA1UEBhMC\nVVMxCzAJBgNVBAgTAldBMRAwDgYDVQQHEwdTZWF0dGxlMQ8wDQYDVQQKEwZBbWF6\nNYiytVbZPQUQ5Yaxu2jXnimvw3rrszlaEXAMPLE=\n-----END CERTIFICATE-----\n",
        "CertificateChain": "-----BEGIN CERTIFICATE-----\nMIICiTCCAfICCQD6m7oRw0uXOjANBgkqhkiG9w0BAQUFADCBiDELMAkGA1UEBhMC\nb24xFDASBgNVBAsTC0lBTSBDb25zb2xlMRIwEAYDVQQDEwlUZXN0Q2lsYWMxHzAd\nNYiytVbZPQUQ5Yaxu2jXnimvw3rrszlaEXAMPLE=\n-----END CERTIFICATE-----\n",
        "PrivateKey": "-----BEGIN ENCRYPTED PRIVATE KEY-----\nMIIFHzBJBgkqhkiG9w0BBQ0wPDAbBgkqhkiG9w0BBQwwDgQIEXAMPLEKEYAgIIADAd\nBglghkgBZQMEASoEEEXAMPLEPRIVATEKEYEXAMPLEEXAMPLE=\n-----END ENCRYPTED PRIVATE KEY-----\n"
    }

To export the certificate, chain, and private key to a local file, use the following command. ::

    aws acm export-certificate \
        --certificate-arn arn:aws:acm:region:account:certificate/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --passphrase file://path-to-passphrase-file > c:\temp\export.txt

For more information, see `Export an AWS Certificate Manager private certificate <https://docs.aws.amazon.com/acm/latest/userguide/export-private.html>`__ in the *AWS Certificate Manager User Guide*.
