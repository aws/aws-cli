**To view the account settings for an account**

The following example shows how to view the effective account settings for an account.

Command::

  aws ecs list-account-settings --effective-settings

Output::

    {
        "settings": [
            {
                "name": "containerInstanceLongArnFormat",
                "value": "enabled",
                "principalArn": "arn:aws:iam::123456789012:root"
            },
            {
                "name": "serviceLongArnFormat",
                "value": "enabled",
                "principalArn": "arn:aws:iam::123456789012:root"
            },
            {
                "name": "taskLongArnFormat",
                "value": "enabled",
                "principalArn": "arn:aws:iam::123456789012:root"
            }
        ]
    }

**To view the account settings for a specific IAM user or IAM role**

The following example shows how to view the account settings for a specific IAM user or IAM role.

Command::

  aws ecs list-account-settings --principal-arn arn:aws:iam::123456789012:user/MyUser

Output::

    {
        "settings": [
            {
                "name": "serviceLongArnFormat",
                "value": "enabled",
                "principalArn": "arn:aws:iam::123456789012:user/MyUser"
            }
        ]
    }