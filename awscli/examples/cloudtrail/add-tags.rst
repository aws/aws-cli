**To add tags to trail**

The following ``add-tags`` example adds tags for ``Trail1``. ::

    aws cloudtrail add-tags \
        --resource-id arn:aws:cloudtrail:us-west-2:123456789012:trail/Trail1 \
        --tags-list Key=name,Value=Alice Key=location,Value=us

This command produces no output.

For more information, see `Managing trails with the AWS CLI <https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-additional-cli-commands.html#cloudtrail-additional-cli-commands-add-tag>`__ in the *AWS CloudTrail User Guide*.
