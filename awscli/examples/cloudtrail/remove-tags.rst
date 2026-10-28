**To remove tags for a trail**

The following ``remove-tags`` example removes the specified tags for ``Trail1``. This command produces no output. ::

    aws cloudtrail remove-tags \
        --resource-id arn:aws:cloudtrail:us-east-1:123456789012:trail/Trail1 \
        --tags-list Key=name Key=location
