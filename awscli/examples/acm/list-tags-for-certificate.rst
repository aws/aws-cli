**To list the tags applied to an ACM Certificate**

The following ``list-tags-for-certificate`` example lists the tags applied to a certificate in your account. ::

    aws acm list-tags-for-certificate \
        --certificate-arn arn:aws:acm:region:account:certificate/12345678-1234-1234-1234-123456789012

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
