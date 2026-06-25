**To delete a destination for CloudWatch RUM extended metrics**

The following ``delete-rum-metrics-destination`` example deletes a destination for CloudWatch RUM extended metrics. ::

    aws rum delete-rum-metrics-destination \
        --app-monitor-name AWSApp \
        --destination Evidently \
        --destination-arn arn:aws:evidently:us-east-1:123456789012:project/petfood/feature/petfood-upsell-text

This command produces no output.

For more information, see `CloudWatch RUM <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-RUM.html>`__ in the *Amazon CloudWatch User Guide*.