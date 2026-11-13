**To list tags for a resource**

The following ``list-tags-for-resource`` example lists the tags for the specified source server. ::

    aws drs list-tags-for-resource \
        --resource-arn arn:aws:drs:us-west-2:123456789012:source-server/s-1234567890abcdef0

Output::

    {
        "tags": {
            "Name": "MySourceServer"
        }
    }

For more information, see `Tagging resources <https://docs.aws.amazon.com/drs/latest/userguide/using-tags.html>`__ in the *AWS Elastic Disaster Recovery User Guide*.
