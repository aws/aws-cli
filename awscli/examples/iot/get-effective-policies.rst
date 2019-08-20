**To list the policies that effect a thing**

The following ``get-effective-policies`` example lists the policies that effect the specified thing group, including policies attached to any groups to which it belongs. ::

    aws iot get-effective-policies \
        --thing-name MyLightBulb \
        --principal "arn:aws:iot:us-west-2:123456789012:cert/4f0ba725787aa94d67d2fca420eca022242532e8b3c58e7465c7778b443fd65e"

Output::

    {
        "effectivePolicies": [
            {
                "policyName": "MyTestGroup_Core-policy",
                "policyArn": "arn:aws:iot:us-west-2:123456789012:policy/MyTestGroup_Core-policy",
                "policyDocument": "{\n  \"Version\": \"2012-10-17\",\n  \"Statement\": [\n    {\n      \"Effect\": \"Allow\",\n      \"Action\": [\n        \"iot:Publish\",\n        \"iot:Subscribe\",\n        \"iot:Connect\",\n        \"iot:Receive\"\n      ],\n      \"Resource\": [\n        \"*\"\n      ]\n    },\n    {\n      \"Effect\": \"Allow\",\n      \"Action\": [\n        \"iot:GetThingShadow\",\n        \"iot:UpdateThingShadow\",\n        \"iot:DeleteThingShadow\"\n      ],\n      \"Resource\": [\n        \"*\"\n      ]\n    },\n    {\n      \"Effect\": \"Allow\",\n      \"Action\": [\n        \"greengrass:*\"\n      ],\n      \"Resource\": [\n        \"*\"\n      ]\n    }\n  ]\n}"
            },
            {
                "policyName": "UpdateDeviceCertPolicy",
                "policyArn": "arn:aws:iot:us-west-2:123456789012:policy/UpdateDeviceCertPolicy",
                "policyDocument": "{ \"Version\": \"2012-10-17\", \"Statement\": [ { \"Effect\": \"Allow\", \"Action\":  \"iot:UpdateCertificate\", \"Resource\": \"*\" } ] }"
            }
        ]
    }

For more information, see `Get Effective Policies for a Thing <https://docs.aws.amazon.com/iot/latest/developerguide/thing-groups.html#group-get-effective-policies>`__ in the *AWS IoT Developers Guide*.
