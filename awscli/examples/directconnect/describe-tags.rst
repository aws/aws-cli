**To describe tags for your AWS Direct Connect resources**

The following ``describe-tags`` example describes the tags for the connection ``dxcon-abcabc12``. ::

    aws directconnect describe-tags \
        --resource-arns arn:aws:directconnect:us-east-1:123456789012:dxcon/dxcon-abcabc12

Output::

    {
        "resourceTags": [
            {
                "resourceArn": "arn:aws:directconnect:us-east-1:123456789012:dxcon/dxcon-abcabc12",
                "tags": [
                    {
                        "value": "VAConnection",
                        "key": "Name"
                    }
                ]
            }
        ]
    }