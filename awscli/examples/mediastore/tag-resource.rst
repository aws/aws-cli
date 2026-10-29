**To add tags to a container**

The following ``tag-resource`` example adds tag keys and values to the specified container. ::

    aws mediastore tag-resource \
        --resource arn:aws:mediastore:us-west-2:123456789012:container/ExampleContainer \
        --tags '[{"Key": "Region", "Value": "West"}, {"Key": "Environment", "Value": "Test"}]'

This command produces no output.

For more information, see `Best practices and strategies <https://docs.aws.amazon.com/tag-editor/latest/userguide/best-practices-and-strats.html>`__ in the *Tagging AWS Resources and Tag Editor User Guide*.
