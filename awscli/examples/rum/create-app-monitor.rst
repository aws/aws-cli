**To create a Amazon CloudWatch RUM app monitor**

The following ``create-app-monitor`` creates a Amazon CloudWatch RUM app monitor. ::

	aws rum create-app-monitor \
		--domain amazonaws.com \
		--name AWSApp

Output::

	{
		"Id": "77gh6a55-bh77-5eed-a338-d8750b544a2"
	}

For more information, see `CloudWatch RUM <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-RUM.html>`__ in the *Amazon CloudWatch User Guide*.