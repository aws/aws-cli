**To update the certificate options**

The following ``update-certificate-options`` example opts out of certificate transparency logging. This command produces no output. ::

    aws acm update-certificate-options \
        --certificate-arn arn:aws:acm:region:account:certificate/12345678-1234-1234-1234-123456789012 \
        --options CertificateTransparencyLoggingPreference=DISABLED

