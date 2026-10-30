**To remove tags for a trail**

The following ``remove-tags`` example removes the specified tags for ``Trail1``. ::

    aws cloudtrail remove-tags \
        --resource-id arn:aws:cloudtrail:us-west-2:123456789012:trail/Trail1 \
        --tags-list Key=name Key=location

This command produces no output.

For more information, see `Managing trails with the AWS CLI <https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-additional-cli-commands.html>`__ in the *AWS CloudTrail User Guide*.
