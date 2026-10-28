**To delete an ACM certificate from your account**

The following ``delete-certificate`` example deletes the certificate with the specified ARN. This command produces no output. ::

    aws acm delete-certificate \
        --certificate-arn arn:aws:acm:region:account:certificate/12345678-1234-1234-1234-123456789012