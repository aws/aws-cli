**To retrieve the service setting for managed instance activation**

This example retrieves the current service setting tier for managed instance activations in the specified region. For more information, see `Using the Advanced-Instances Tier`_ in the *AWS Systems Manager User Guide*.

.. _`Using the Advanced-Instances Tier`: https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-managedinstances-advanced.html

Command::

   aws ssm get-service-setting --setting-id arn:aws:ssm:us-east-1:123456789012:servicesetting/ssm/managed-instance/activation-tier
   
Output::

  {
      "ServiceSetting": {
          "SettingId": "/ssm/managed-instance/activation-tier",
          "SettingValue": "standard",
          "LastModifiedDate": 1550708144.058,
          "LastModifiedUser": "System",
          "ARN": "arn:aws:ssm:us-east-1:123456789012:servicesetting/ssm/managed-instance/activation-tier",
          "Status": "Default"
      }
  }

**To retrieve the service setting for Parameter Store throughput**

This example retrieves the current service setting for Parameter Store throughput in the specified region. For more information, see `Increasing Parameter Store Throughput`_ in the *AWS Systems Manager User Guide*.

.. _`Increasing Parameter Store Throughput`: https://docs.aws.amazon.com/systems-manager/latest/userguide/parameter-store-throughput.html

Command::

   aws ssm get-service-setting --setting-id arn:aws:ssm:us-east-1:123456789012:servicesetting/ssm/parameter-store/high-throughput-enabled
   
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
