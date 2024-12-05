**To Disassociate a KMS key with the log group**

The following ``disassociate-kms-key`` example disassociates KMS key with the log group named ``demo-log-group``. If the command succeeds, no output is returned. ::

    aws logs disassociate-kms-key \
        --log-group-name demo-log-group \

For more information, see `Encrypt log data in CloudWatch Logs using AWS Key Management Service <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/encrypt-log-data-kms.html>`__ in the *Amazon CloudWatch Logs User Guide*.