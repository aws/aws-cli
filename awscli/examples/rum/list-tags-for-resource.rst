**To display the tags associated with a CloudWatch RUM resource**

The following ``list-tags-for-resource`` displays the tags associated with a CloudWatch RUM resource. ::

	aws rum list-tags-for-resource \
		--resource-arn arn:aws:rum:us-west-1:123456789012:appmonitor/MyWebApp 

Output::

	{
		"Tags": {
			"Value": "Production",
			"delete": "no",
			"Key": "Environment",
			"MyWebApp": ""
		}
	}

For more information, see `CloudWatch RUM <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-RUM.html>`__ in the *Amazon CloudWatch User Guide*.