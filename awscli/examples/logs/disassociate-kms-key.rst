**To disassociate a KMS key with the log group**

The following ``disassociate-kms-key`` example disassociates KMS key with the log group named ``demo-log-group``. ::

    aws logs disassociate-kms-key \
        --log-group-name demo-log-group

This command produces no output.

For more information, see `Encrypt log data in CloudWatch Logs using AWS Key Management Service <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/encrypt-log-data-kms.html>`__ in the *Amazon CloudWatch Logs User Guide*.