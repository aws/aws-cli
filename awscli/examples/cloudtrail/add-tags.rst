**To add tags to trail**

The following ``add-tags`` example adds tags for ``Trail1``. This command produces no output. ::

    aws cloudtrail add-tags \
        --resource-id arn:aws:cloudtrail:us-east-1:123456789012:trail/Trail1 \
        --tags-list Key=name,Value=Alice Key=location,Value=us
