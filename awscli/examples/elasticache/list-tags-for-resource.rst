**To list events**

The following ``list-tags-for-resource`` example lists the tags for a cache cluster. ::

    aws elasticache list-tags-for-resource \
        --resource-name "arn:aws:elasticache:us-east-1:123456789012:cluster:my-cluster"

Output::

    {
        "TagList": [
            {
                "Key": "Project",
                "Value": "querySpeedUp"
            },
            {
                "Key": "Environment",
                "Value": "PROD"
            }
        ]
    }

For more information, see `Listing Tags Using the AWS CLI < https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/Tagging.Managing.CLI.html#Tagging.Managing.CLI.List>`__ in the *Amazon ElastiCache for Redis User Guide*.
