The following command gets the attributes of a topic named ``my-topic``::

  aws sns get-topic-attributes --topic-arn "arn:aws:sns:us-west-2:0123456789012:my-topic"

Output::

  {
      "Attributes": {
          "SubscriptionsConfirmed": "1",
          "DisplayName": "my-topic",
          "SubscriptionsDeleted": "0",
          "EffectiveDeliveryPolicy": "{\"http\":{\"defaultHealthyRetryPolicy\":{\"minDelayTarget\":20,\"maxDelayTarget\":20,\"numRetries\":3,\"numMaxDelayRetries\":0,\"numNoDelayRetries\":0,\"numMinDelayRetries\":0,\"backoffFunction\":\"linear\"},\"disableSubscriptionOverrides\":false}}",
          "Owner": "0123456789012",
          "Policy": "{\"Version\":\"2008-10-17\",\"Id\":\"__default_policy_ID\",\"Statement\":[{\"Sid\":\"__default_statement_ID\",\"Effect\":\"Allow\",\"Principal\":{\"AWS\":\"*\"},\"Action\":[\"SNS:Subscribe\",\"SNS:ListSubscriptionsByTopic\",\"SNS:DeleteTopic\",\"SNS:GetTopicAttributes\",\"SNS:Publish\",\"SNS:RemovePermission\",\"SNS:AddPermission\",\"SNS:Receive\",\"SNS:SetTopicAttributes\"],\"Resource\":\"arn:aws:sns:us-west-2:0123456789012:my-topic\",\"Condition\":{\"StringEquals\":{\"AWS:SourceOwner\":\"0123456789012\"}}}]}",
          "TopicArn": "arn:aws:sns:us-west-2:0123456789012:my-topic",
          "SubscriptionsPending": "0"
      }
  }
