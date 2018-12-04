The following command gets the attributes of a subscription to a topic named ``my-topic``::

  aws sns get-subscription-attributes --subscription-arn "arn:aws:sns:us-west-2:0123456789012:my-topic:8a21d249-4329-4871-acc6-7be709c6ea7f"

The ``subscription-arn`` is available in the output of ``aws sns list-subscriptions``.

Output::

  {
      "Attributes": {
          "Endpoint": "my-email@example.com",
          "Protocol": "email",
          "RawMessageDelivery": "false",
          "ConfirmationWasAuthenticated": "false",
          "Owner": "0123456789012",
          "SubscriptionArn": "arn:aws:sns:us-west-2:0123456789012:my-topic:8a21d249-4329-4871-acc6-7be709c6ea7f",
          "TopicArn": "arn:aws:sns:us-west-2:0123456789012:my-topic"
      }
  }