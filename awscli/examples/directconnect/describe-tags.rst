**To describe tags for your AWS Direct Connect resources**

The following ``describe-tags`` example describes the tags for the connection ``dxcon-abcabc12``. ::

    aws directconnect describe-tags \
        --resource-arns arn:aws:directconnect:us-west-2:123456789012:dxcon/dxcon-abcabc12

Output::

    {
        "resourceTags": [
            {
                "resourceArn": "arn:aws:directconnect:us-west-2:123456789012:dxcon/dxcon-abcabc12",
                "tags": [
                    {
                        "value": "VAConnection",
                        "key": "Name"
                    }
                ]
            }
        ]
    }

For more information, see `Tag AWS Direct Connect resources <https://docs.aws.amazon.com/directconnect/latest/UserGuide/using-tags.html>`__ in the *AWS Direct Connect User Guide*.
