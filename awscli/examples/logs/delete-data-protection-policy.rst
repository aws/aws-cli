**To Delete the data protection policy from the specified log group**

The following ``delete-data-protection-policy`` example deletes the data protection policy from the log group named ``demo-log-group``. If the command succeeds, no output is returned. ::

    aws logs delete-data-protection-policy \
        --log-group-identifier demo-log-group

For more information, see `Help protect sensitive log data with masking <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/mask-sensitive-log-data.html>`__ in the *Amazon CloudWatch Logs User Guide*.