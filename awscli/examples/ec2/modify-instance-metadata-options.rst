**Example 1: To enable IMDSv2**

The following ``modify-instance-metadata-options`` example configures the use of IMDSv2 on the specified instance. ::

    aws ec2 modify-instance-metadata-options \
        --instance-id i-1234567898abcdef0 \
        --http-tokens required \
        --http-endpoint enabled

Output::

    {
        "InstanceId": "i-1234567898abcdef0",
        "InstanceMetadataOptions": {
            "State": "pending",
            "HttpTokens": "required",
            "HttpPutResponseHopLimit": 1,
            "HttpEndpoint": "enabled"
        }
    }

For more information, see `Instance metadata and user data <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-metadata.html>`__ in the *Amazon Elastic Compute Cloud User Guide for Linux Instances*.
 
**Example 2: To disable instance metadata**

The following ``modify-instance-metadata-options`` example disables the use of all versions of instance metadata on the specified instance. ::

    aws ec2 modify-instance-metadata-options \
        --instance-id i-1234567898abcdef0 \
        --http-endpoint disabled

Output::

    {
        "InstanceId": "i-1234567898abcdef0",
        "InstanceMetadataOptions": {
            "State": "pending",
            "HttpTokens": "required",
            "HttpPutResponseHopLimit": 1,
            "HttpEndpoint": "disabled"
        }
    }

For more information, see `Instance metadata and user data <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-metadata.html>`__ in the *Amazon Elastic Compute Cloud User Guide for Linux Instances*.
