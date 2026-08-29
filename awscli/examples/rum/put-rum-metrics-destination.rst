**To create or update a destination to receive extended metrics from CloudWatch RUM**

The following ``put-rum-metrics-destination`` example creates or updates a destination to receive extended metrics from CloudWatch RUM. ::

    aws rum put-rum-metrics-destination \
        --app-monitor-name MyWebApp \
        --destination Evidently \
        --destination-arn arn:aws:evidently:us-east-1:123456789012:project/petfood/feature/petfood-upsell-text \
        --iam-role-arn arn:aws:iam::123456789012:role/Assume-role-EC2 
        
This command produces no output.

For more information, see `CloudWatch RUM <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-RUM.html>`__ in the *Amazon CloudWatch User Guide*.