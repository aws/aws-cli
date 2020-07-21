**To get summary information about channels**

The following ``list-channels`` example lists all channels for your AWS account. ::

    aws ivs list-channels

Output::

    {
        "channels": [
            {
                "arn": "arn:aws:ivs:us-west-2:123456789012:channel/abcdABCDefgh",
                "name": "channel-1",
                "latencyMode": "LOW",
                "tags": {}
            },
            {
                "arn": "arn:aws:ivs:us-west-2:123456789012:channel/abcdABCDefgh",
                "name": "channel-2",
                "latencyMode": "LOW",
                "tags": {}
            }
        ]
    }

For more information, see `Create a Channel <https://docs.aws.amazon.com/ivs/latest/userguide/GSIVS-create-channel.html>`__ in the *Amazon Interactive Video Service User Guide*.