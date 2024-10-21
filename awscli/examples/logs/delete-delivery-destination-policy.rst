**To delete a delivery destination policy**

The following ``delete-delivery-destination-policy`` example deletes the policy for delivery destination named ``demo-delivery-destination``. ::

     aws logs delete-delivery-destination-policy \
        --delivery-destination-name demo-delivery-destination

This command produces no output.

For more information, see `Enable logging from AWS services <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AWS-logs-and-resource-policy.html>`__ in the *Amazon CloudWatch Logs User Guide*.