**To retrieve the data protection policy from an Amazon SNS topic**

The following `get-data-protection-policy` example retrieves the data protection policy from the specified Amazon SNS topic. ::

    aws sns get-data-protection-policy \
        --resource-arn arn:aws:sns:us-east-1:123456789012:MyTopic

Output::

  {
    "DataProtectionPolicy": "{\"Name\":\"__example_data_protection_policy\",\"Description\":\"Example data protection policy\",\"Version\":\"2021-06-01\",\"Statement\":[{\"DataDirection\":\"Inbound\",\"Principal\":[\"*\"],\"DataIdentifier\":[\"arn:aws:dataprotection::aws:data-identifier/CreditCardNumber\"],\"Operation\":{\"Audit\":{\"SampleRate\":\"99\",\"FindingsDestination\":{\"CloudWatchLogs\":{\"LogGroup\":\"<example log name>\"},\"Firehose\":{\"DeliveryStream\":\"<example stream name>\"},\"S3\":{\"Bucket\":\"<example bucket name>\"}}}}}]}"
  }