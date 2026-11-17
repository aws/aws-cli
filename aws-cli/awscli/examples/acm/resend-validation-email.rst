**To resend validation email for your ACM certificate request**

The following ``resend-validation-email`` example tells the Amazon certificate authority to send validation email to the appropriate addresses. ::

    aws acm resend-validation-email \
        --certificate-arn arn:aws:acm:region:account:certificate/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --domain www.example.com \
        --validation-domain example.com

This command produces no output.

For more information, see `AWS Certificate Manager email validation <https://docs.aws.amazon.com/acm/latest/userguide/email-validation.html>`__ in the *AWS Certificate Manager User Guide*.
