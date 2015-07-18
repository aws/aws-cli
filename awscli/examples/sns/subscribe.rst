The following command subscribes an email address to a topic::

  aws sns subscribe --topic-arn arn:aws:sns:us-west-2:0123456789012:my-topic --protocol email --notification-endpoint my-email@example.com

Output::

  {
      "SubscriptionArn": "pending confirmation"
  }
