**To list tags of a DynamoDB resource**

The following ``list-tags-of-resource`` example displays tags for the ``MusicCollection`` table. ::

    aws dynamodb list-tags-of-resource \
        --resource-arn arn:aws:dynamodb:us-west-2:123456789012:table/MusicCollection

Output::

    {
        "Tags": [
            {
                "Key": "Owner",
                "Value": "blueTeam"
            }
        ]
    }

For more information, see `Tagging for DynamoDB <https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Tagging.html>`__ in the *Amazon DynamoDB Developer Guide*.
