**To list tags for a container**

The following ``list-tags-for-resource`` example displays the tag keys and values assigned to the specified container. ::

    aws mediastore list-tags-for-resource \
        --resource arn:aws:mediastore:us-west-2:1213456789012:container/ExampleContainer

Output::

    {
        "Tags": [
            {
                "Value": "Test",
                "Key": "Environment"
            },
            {
                "Value": "West",
                "Key": "Region"
            }
        ]
    }

For more information, see `Best practices and strategies <https://docs.aws.amazon.com/tag-editor/latest/userguide/best-practices-and-strats.html>`__ in the *Tagging AWS Resources and Tag Editor User Guide*.
