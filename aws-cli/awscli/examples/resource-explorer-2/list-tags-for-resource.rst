**To list the tags attached to a Resource Explorer view or index**

The following ``list-tags-for-resource`` example lists the tag key and value pairs attached to view with the specified ARN. You must call the operation from the AWS Region that contains the resource. ::

    aws resource-explorer-2 list-tags-for-resource \
        --resource-arn arn:aws:resource-explorer-2:us-west-2:123456789012:view/My-View/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "Tags": {
            "application": "MainCorpApp",
            "department": "1234"
        }
    }

For more information about tagging views, see `Adding tags to views <https://docs.aws.amazon.com/resource-explorer/latest/userguide/configure-views-tag.html>`__ in the *AWS Resource Explorer Users Guide*.