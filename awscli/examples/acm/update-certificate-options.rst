**To update the certificate options**

The following ``update-certificate-options`` example opts out of certificate transparency logging. ::

    aws acm update-certificate-options \
        --certificate-arn arn:aws:acm:region:account:certificate/12345678-1234-1234-1234-123456789012 \
        --options CertificateTransparencyLoggingPreference=DISABLED

This command produces no output.

For more information, see `Certificate Transparency Logging <https://docs.aws.amazon.com/acm/latest/userguide/acm-concepts.html#concept-transparency>`__ in the *AWS Certificate Manager User Guide*.
