**To add tags to an existing ACM Certificate**

The following ``add-tags-to-certificate`` example adds two tags to the specified certificate. Use a space to separate multiple tags. ::

    aws acm add-tags-to-certificate \
        --certificate-arn arn:aws:acm:region:account:certificate/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --tags Key=Admin,Value=Alice Key=Purpose,Value=Website

This command produces no output.

For more information, see `Tag AWS Certificate Manager resources <https://docs.aws.amazon.com/acm/latest/userguide/tags.html>`__ in the *AWS Certificate Manager User Guide*.
