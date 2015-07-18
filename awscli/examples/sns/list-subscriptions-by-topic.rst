The following command retrieves a list of SNS subscriptions::

  aws sns list-subscriptions-by-topic --topic-arn "arn:aws:sns:us-west-2:0123456789012:my-topic"

Output::

  {
      "Subscriptions": [
          {
              "Owner": "0123456789012",
              "Endpoint": "my-email@example.com",
              "Protocol": "email",
              "TopicArn": "arn:aws:sns:us-west-2:0123456789012:my-topic",
              "SubscriptionArn": "arn:aws:sns:us-west-2:0123456789012:my-topic:8a21d249-4329-4871-acc6-7be709c6ea7f"
          }
      ]
  }
