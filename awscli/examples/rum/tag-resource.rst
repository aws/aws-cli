**To assigns one or more tags (key-value pairs) to the specified CloudWatch resource**

The following ``tag-resource`` assigns one or more tags (key-value pairs) to the specified CloudWatch resource. If the command succeeds, no output is returned. ::

	aws rum tag-resource \
		--resource-arn arn:aws:rum:us-west-1:123456789012:appmonitor/MyWebApp \
		--tags Key=Environment,Value=Production

For more information, see `CloudWatch RUM <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-RUM.html>`__ in the *Amazon CloudWatch User Guide*.