**To remove tags from a container**

The following ``untag-resource`` example removes the specified tag key and its associated value from a container. ::

    aws mediastore untag-resource \
        --resource arn:aws:mediastore:us-west-2:123456789012:container/ExampleContainer \
        --tag-keys Region

This command produces no output.

For more information, see `Best practices and strategies <https://docs.aws.amazon.com/tag-editor/latest/userguide/best-practices-and-strats.html>`__ in the *Tagging AWS Resources and Tag Editor User Guide*.
