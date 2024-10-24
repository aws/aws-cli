**To retrieve the complete configuration information for one app monitor**

The following ``get-app-monitor`` retrieves the complete configuration information for one app monitor. ::

	aws rum get-app-monitor \
		--name MyWebApp

Output::

	{
		"AppMonitor": {
			"AppMonitorConfiguration": {
				"AllowCookies": true,
				"EnableXRay": true,
				"ExcludedPages": [],
				"IdentityPoolId": "us-west-1:78bcaws1-5e48-4as6-8tu4-t8c62d152d38",
				"IncludedPages": [],
				"SessionSampleRate": 1.0,
				"Telemetries": [
					"performance",
					"errors",
					"http"
				]
			},
			"Created": "2024-04-04T16:13:09.278943Z",
			"CustomEvents": {
				"Status": "ENABLED"
			},
			"DataStorage": {
				"CwLog": {
					"CwLogEnabled": true,
					"CwLogGroup": "/aws/vendedlogs/RUMService_MyWebAppe678de"
				}
			},
			"Domain": "*.amazonaws.com",
			"Id": "r6fj89df-5rt3-55h6-9875-bg6c7uud94fg",
			"Name": "MyWebApp",
			"State": "CREATED",
			"Tags": {
				"auto-delete": "no",
				"MyWebApp": ""
			}
		}
	}

For more information, see `CloudWatch RUM <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-RUM.html>`__ in the *Amazon CloudWatch User Guide*.