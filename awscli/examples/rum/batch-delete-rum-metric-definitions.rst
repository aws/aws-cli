**To remove the specified metrics from being sent to an extended metrics destination**

The following ``batch-delete-rum-metric-definitions`` removes the specified metrics from being sent to an extended metrics destination. If the command succeeds, no output is returned. ::

	aws rum batch-delete-rum-metric-definitions \
		--app-monitor-name AWSApp \
		--destination Evidently \
		--destination-arn arn:aws:evidently:us-east-1:123456789012:project/petfood/feature/petfood-upsell-text \
		--metric-definition-ids 77gh6a55-bh77-5eed-a338-d8750b544a2

For more information, see `CloudWatch RUM <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-RUM.html>`__ in the *Amazon CloudWatch User Guide*.