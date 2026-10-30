**To list the tags applied to an ACM Certificate**

The following ``list-tags-for-certificate`` example lists the tags applied to a certificate in your account. ::

    aws acm list-tags-for-certificate \
        --certificate-arn arn:aws:acm:region:account:certificate/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "Tags": [
            {
                "Value": "Website",
                "Key": "Purpose"
            },
            {
                "Value": "Alice",
                "Key": "Admin"
            }
        ]
    }

For more information, see `Tag AWS Certificate Manager resources <https://docs.aws.amazon.com/acm/latest/userguide/tags.html>`__ in the *AWS Certificate Manager User Guide*.
