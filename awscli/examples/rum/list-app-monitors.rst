**To return a list of the Amazon CloudWatch RUM app monitors in the account**

The following ``list-app-monitors`` returns a list of the Amazon CloudWatch RUM app monitors in the account. ::

	aws rum list-app-monitors

Output::

	{
		"AppMonitorSummaries": [
			{
				"Created": "2024-04-07T12:37:05.326459Z",
				"Id": "5bh7juu8-3dd7-4ccu-b434-8e5t89849g9d",
				"Name": "AWSApp",
				"State": "CREATED"
			},
			{
				"Created": "2024-04-07T12:37:10.757704Z",
				"Id": "6f177feb-fbft-4b7j-98k0-86yuc79c6563",
				"Name": "AWSApp2",
				"State": "CREATED"
			},
			{
				"Created": "2024-04-07T12:37:15.330147Z",
				"Id": "dedc2978-8f89-6jju-ad7i-67668kf086b91",
				"Name": "AWSApp3",
				"State": "CREATED"
			},
			{
				"Created": "2024-04-04T16:13:09.278943Z",
				"Id": "r6fj89df-5rt3-55h6-9875-bg6c7uud94fg",
				"Name": "MyWebApp",
				"State": "CREATED"
			}
		]
	}

For more information, see `CloudWatch RUM <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-RUM.html>`__ in the *Amazon CloudWatch User Guide*.