**To view a container policy**

The following ``get-container-policy`` example displays the resource-based policy of the specified container. ::

    aws mediastore get-container-policy \
        --container-name ExampleLiveDemo

Output::

    {
        "Policy": "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Sid\":\"PublicReadOverHttps\",\"Effect\":\"Allow\",\"Principal\":{\"AWS\":\"arn:aws:iam::123456789012:root\"},\"Action\":[\"mediastore:GetObject\",\"mediastore:DescribeObject\"],\"Resource\":\"arn:aws:mediastore:us-west-2:123456789012:container/ExampleLiveDemo/\",\"Condition\":{\"Bool\":{\"aws:SecureTransport\":\"true\"}}}]}"
    }
