**To associate a KMS key with the log group**

The following ``associate-kms-key`` example associates KMS key with log group named ``demo-log-group``. ::

    aws logs associate-kms-key \
        --log-group-name demo-log-group \
        --kms-key-id 1234abcd-12ab-34cd-56ef-1234567890ab

This command produces no output.

For more information, see `Encrypt log data in CloudWatch Logs using AWS Key Management Service <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/encrypt-log-data-kms.html>`__ in the *Amazon CloudWatch Logs User Guide*.