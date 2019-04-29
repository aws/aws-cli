**To reset the service setting for Parameter Store throughput**

This example resets the service setting for Parameter Store throughput in the specified region to no longer use increased throughput. For more information, see `Increasing Parameter Store Throughput`_ in the *AWS Systems Manager User Guide*.

.. _`Increasing Parameter Store Throughput`: https://docs.aws.amazon.com/systems-manager/latest/userguide/parameter-store-throughput.html

Command::

   aws ssm reset-service-setting --setting-id arn:aws:ssm:us-east-1:123456789012:servicesetting/ssm/parameter-store/high-throughput-enabled

Output::

  {
      "ServiceSetting": {
          "SettingId": "/ssm/parameter-store/high-throughput-enabled",
          "SettingValue": "false",
          "LastModifiedDate": 1555532818.578,
          "LastModifiedUser": "System",
          "ARN": "arn:aws:ssm:us-east-1:123456789012:servicesetting/ssm/parameter-store/high-throughput-enabled",
          "Status": "Default"
      }
  }
