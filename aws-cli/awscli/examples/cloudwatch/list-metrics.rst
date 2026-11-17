**To list the metrics for Amazon SNS**

The following ``list-metrics`` example displays the metrics for Amazon SNS. ::

    aws cloudwatch list-metrics \
        --namespace "AWS/SNS"

Output::

    {
        "Metrics": [
            {
                "Namespace": "AWS/SNS",
                "Dimensions": [
                    {
                        "Name": "TopicName",
                        "Value": "NotifyMe"
                    }
                ],
                "MetricName": "PublishSize"
            },
            {
                "Namespace": "AWS/SNS",
                "Dimensions": [
                    {
                        "Name": "TopicName",
                        "Value": "CFO"
                    }
                ],
                "MetricName": "PublishSize"
            },
            {
                "Namespace": "AWS/SNS",
                "Dimensions": [
                    {
                        "Name": "TopicName",
                        "Value": "NotifyMe"
                    }
                ],
                "MetricName": "NumberOfNotificationsFailed"
            },
            {
                "Namespace": "AWS/SNS",
                "Dimensions": [
                    {
                        "Name": "TopicName",
                        "Value": "NotifyMe"
                    }
                ],
                "MetricName": "NumberOfNotificationsDelivered"
            },
            {
                "Namespace": "AWS/SNS",
                "Dimensions": [
                    {
                        "Name": "TopicName",
                        "Value": "NotifyMe"
                    }
                ],
                "MetricName": "NumberOfMessagesPublished"
            },
            {
                "Namespace": "AWS/SNS",
                "Dimensions": [
                    {
                        "Name": "TopicName",
                        "Value": "CFO"
                    }
                ],
                "MetricName": "NumberOfMessagesPublished"
            },
            {
                "Namespace": "AWS/SNS",
                "Dimensions": [
                    {
                        "Name": "TopicName",
                        "Value": "CFO"
                    }
                ],
                "MetricName": "NumberOfNotificationsDelivered"
            },
            {
                "Namespace": "AWS/SNS",
                "Dimensions": [
                    {
                        "Name": "TopicName",
                        "Value": "CFO"
                    }
                ],
                "MetricName": "NumberOfNotificationsFailed"
            }
        ]
    }

For more information, see `View available metrics <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/viewing_metrics_with_cloudwatch.html>`__ in the *Amazon CloudWatch User Guide*.
