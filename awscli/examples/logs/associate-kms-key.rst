**To Associate a KMS key with the log group**

The following ``associate-kms-key`` example associates KMS key with log group named ``demo-log-group``. If the command succeeds, no output is returned. ::

    aws logs associate-kms-key \
        --log-group-name demo-log-group \
        --kms-key-id ``KMS_KEY_ID_ARN``

For more information, see `Encrypt log data in CloudWatch Logs using AWS Key Management Service <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/encrypt-log-data-kms.html>`__ in the *Amazon CloudWatch Logs User Guide*.