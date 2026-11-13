**To remove tags from a resource**

The following ``untag-resource`` example removes the specified tags from a source server. ::

    aws drs untag-resource \
        --resource-arn arn:aws:drs:us-west-2:123456789012:source-server/s-1234567890abcdef0 \
        --tag-keys Environment Team

This command produces no output.

For more information, see `Tagging resources <https://docs.aws.amazon.com/drs/latest/userguide/using-tags.html>`__ in the *AWS Elastic Disaster Recovery User Guide*.
