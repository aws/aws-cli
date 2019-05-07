**To modify the default account settings**

The following example shows how to modify the default account setting for all IAM users or roles on your account. These changes apply to the entire AWS account unless an IAM user or role explicitly overrides these settings for themselves.

Command::

  aws ecs put-account-setting-default --name serviceLongArnFormat --value enabled

Output::

    {
        "setting": {
            "name": "serviceLongArnFormat",
            "value": "enabled",
            "principalArn": "arn:aws:iam::123456789012:root"
        }
    }
