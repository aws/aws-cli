**To delete an ACM certificate from your account**

The following ``delete-certificate`` example deletes the certificate with the specified ARN. ::

    aws acm delete-certificate \
        --certificate-arn arn:aws:acm:region:account:certificate/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

This command produces no output.

For more information, see `Delete certificates managed by AWS Certificate Manager <https://docs.aws.amazon.com/acm/latest/userguide/gs-acm-delete.html>`__ in the *AWS Certificate Manager User Guide*.
