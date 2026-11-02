**To remove a tag from an ACM Certificate**

The following ``remove-tags-from-certificate`` example removes two tags from the specified certificate. Use a space to separate multiple tags. ::

    aws acm remove-tags-from-certificate \
        --certificate-arn arn:aws:acm:region:account:certificate/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --tags Key=Admin,Value=Alice Key=Purpose,Value=Website

This command produces no output.

For more information, see `Tag AWS Certificate Manager resources <https://docs.aws.amazon.com/acm/latest/userguide/tags.html>`__ in the *AWS Certificate Manager User Guide*.
