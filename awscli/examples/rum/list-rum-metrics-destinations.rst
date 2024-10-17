**To return a list of destinations that you have created to receive RUM extended metrics, for the specified app monitor**

The following ``list-rum-metrics-destinations`` returns a list of destinations that you have created to receive RUM extended metrics, for the specified app monitor. ::

	aws rum list-rum-metrics-destinations \
		--app-monitor-name MyWebApp  

Output::

	{
		"Destinations": [
			{
				"Destination": "CloudWatch",
				"DestinationArn": "",
				"IamRoleArn": ""
			},
			{
				"Destination": "Evidently",
				"DestinationArn": "arn:aws:evidently:us-east-1:123456789012:project/petfood/feature/petfood-upsell-text",
				"IamRoleArn": "arn:aws:iam::123456789012:role/Assume-role-EC2"
			}
		]
	}

For more information, see `CloudWatch RUM <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-RUM.html>`__ in the *Amazon CloudWatch User Guide*.