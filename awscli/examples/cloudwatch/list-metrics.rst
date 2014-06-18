**To list the metrics for Amazon EC2**

The following example uses the ``list-metrics`` command to list the metrics for Amazon SNS.::

  aws cloudwatch list-metrics --namespace "AWS/SNS"

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

