**To delete the account settings for a specific IAM user or IAM role**

The following ``delete-account-setting`` example deletes the account settings for the specific IAM user or IAM role. ::

    aws ecs delete-account-setting \
        --name serviceLongArnFormat \
        --principal-arn arn:aws:iam::123456789012:user/MyUser

Output::

    {
        "setting": {
            "name": "serviceLongArnFormat",
            "value": "enabled",
            "principalArn": "arn:aws:iam::123456789012:user/MyUser"
        }
    }

For more information, see `Access Amazon ECS features with account settings <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs-account-settings.html>`__ in the *Amazon ECS Developer Guide*.
