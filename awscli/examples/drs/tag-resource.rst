**To tag a resource**

The following ``tag-resource`` example adds tags to the specified source server. ::

    aws drs tag-resource \
        --resource-arn arn:aws:drs:us-west-2:123456789012:source-server/s-1234567890abcdef0 \
        --tags Environment=Production,Team=DisasterRecovery

This command produces no output.

For more information, see `Tagging resources <https://docs.aws.amazon.com/drs/latest/userguide/using-tags.html>`__ in the *AWS Elastic Disaster Recovery User Guide*.
