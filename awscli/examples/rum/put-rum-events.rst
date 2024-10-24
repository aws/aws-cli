**To send telemetry events about your application performance and user behavior to CloudWatch RUM**

The following ``put-rum-events`` sends telemetry events about your application performance and user behavior to CloudWatch RUM. If the command succeeds, no output is returned. ::

	aws rum put-rum-events \
		--app-monitor-details "{\"id\":\"r6fj89df-5rt3-55h6-9875-bg6c7uud94fg\",\"name\":\"MyWebApp\",\"version\":\"1.0.0\"}" \
		--batch-id "0b856678-90g1-4767-9uu6-ceyui23567807" \
		--id "r6fj89df-5rt3-55h6-9875-bg6c7uud94fg" \
		--rum-events "[{\"details\":\"{\\\"version\\\":\\\"1.0.0\\\",\\\"targetUrl\\\":\\\"https://amazonaws.com\\\",\\\"initiatorType\\\":\\\"other\\\",\\\"startTime\\\":2838.7000000178814,\\\"duration\\\":257.7999999821186,\\\"transferSize\\\":496.0,\\\"fileType\\\":\\\"image\\\"}\",\"id\":\"r6fj89df-5rt3-55h6-9875-bg6c7uud94fg\",\"metadata\":\"{\\\"version\\\":\\\"1.0.0\\\",\\\"browserLanguage\\\":\\\"en-GB\\\",\\\"browserName\\\":\\\"Chrome\\\",\\\"browserVersion\\\":\\\"123.0.0.0\\\",\\\"osName\\\":\\\"Mac OS\\\",\\\"osVersion\\\":\\\"10.15.7\\\",\\\"deviceType\\\":\\\"desktop\\\",\\\"platformType\\\":\\\"web\\\",\\\"pageId\\\":\\\"/\\\",\\\"interaction\\\":0,\\\"title\\\":\\\"Simple HTML Website\\\",\\\"domain\\\":\\\"amazonaws.com\\\",\\\"aws:client\\\":\\\"arw-script\\\",\\\"aws:clientVersion\\\":\\\"1.16.1\\\",\\\"countryCode\\\":\\\"IN\\\",\\\"subdivisionCode\\\":\\\"KA\\\"}\",\"timestamp\":1712982698,\"type\":\"com.amazon.rum.performance_resource_event\"}]" \
		--user-details "{\"sessionId\":\"696bb1ce-f193-4240-be00-aeaf4c2a5614\",\"userId\":\"8b43f0t6-8ce7-5a1c-90d2-b1771h7a1bbb\"}"

For more information, see `CloudWatch RUM <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-RUM.html>`__ in the *Amazon CloudWatch User Guide*.