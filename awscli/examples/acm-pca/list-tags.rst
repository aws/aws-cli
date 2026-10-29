**To list the tags for your certificate authority**

The following ``list-tags`` example lists the tags associated with the private CA specified by the ARN. ::

    aws acm-pca list-tags \
        --certificate-authority-arn arn:aws:acm-pca:us-west-2:123456789012:certificate-authority/123455678-1234-1234-1234-123456789012 \
        --max-results 10

Output::

    {
        "Tags": [
            {
                "Key": "Admin",
                "Value": "Alice"
            },
            {
                "Key": "Purpose",
                "Value": "Website"
            }
        ]
    }

For more information, see `Add tags for your private CA <https://docs.aws.amazon.com/privateca/latest/userguide/PcaCaTagging.html>`__ in the *AWS Private Certificate Authority User Guide*.
