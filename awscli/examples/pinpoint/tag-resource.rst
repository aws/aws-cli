**To add tags to a resource**

The following ``tag-resource`` example adds two tags (key names and values) to a resource. ::

    aws pinpoint tag-resource \
        --resource-arn arn:aws:mobiletargeting:us-west-2:AIDACKCEVSQ6C2EXAMPLE:apps/810c7aab86d42fb2b56c8c966example \
        --tags-model tags={Stack=Production,Year=2019}

This command produces no output.

For more information, see `Manage Amazon Pinpoint resource tags <https://docs.aws.amazon.com/pinpoint/latest/developerguide/tagging-resources.html>`__ in the *Amazon Pinpoint Developer Guide*.
