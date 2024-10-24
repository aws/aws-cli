**To Delete a CloudWatch Logs account policy**

The following ``delete-account-policy`` example deletes a CloudWatch Logs account policy. If the command succeeds, no output is returned. ::

    aws logs delete-account-policy \
        --policy-name Example_Data_Protection_Policy \
        --policy-type DATA_PROTECTION_POLICY

For more information, see `Help protect sensitive log data with masking <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/mask-sensitive-log-data.html>`__ in the *Amazon CloudWatch Logs User Guide*.