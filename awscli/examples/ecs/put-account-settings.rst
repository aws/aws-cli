**To modify the account settings for a specific IAM user or IAM role**

The following example shows how to view the account settings for a specific IAM user or IAM role.

Command::

  aws ecs put-account-setting --name serviceLongArnFormat --value enabled --principal-arn arn:aws:iam::123456789012:user/MyUser

Output::

    {
        "setting": {
            "name": "serviceLongArnFormat",
            "value": "enabled",
            "principalArn": "arn:aws:iam::123456789012:user/MyUser"
        }
    }
