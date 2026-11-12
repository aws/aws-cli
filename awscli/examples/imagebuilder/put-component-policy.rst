**To share a component with another AWS account**

The following ``put-component-policy`` example applies a resource policy to a component build version that grants another AWS account permission to view the component and use it in its own image recipes. ::

    aws imagebuilder put-component-policy \
        --component-arn arn:aws:imagebuilder:us-west-2:123456789012:component/my-shared-component/1.0.0/1 \
        --policy file://component-policy.json

Contents of ``component-policy.json``::

    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "AWS": "arn:aws:iam::123456789111:root"
                },
                "Action": [
                    "imagebuilder:GetComponent",
                    "imagebuilder:ListComponents"
                ],
                "Resource": [
                    "arn:aws:imagebuilder:us-west-2:123456789012:component/my-shared-component/1.0.0/1"
                ]
            }
        ]
    }

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "componentArn": "arn:aws:imagebuilder:us-west-2:123456789012:component/my-shared-component/1.0.0/1"
    }

For more information, see `Share Image Builder resources with AWS RAM <https://docs.aws.amazon.com/imagebuilder/latest/userguide/manage-shared-resources.html>`__ in the *EC2 Image Builder User Guide*.
