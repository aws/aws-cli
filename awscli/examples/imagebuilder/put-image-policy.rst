**To share an image with another AWS account**

The following ``put-image-policy`` example applies a resource policy to an image build version that grants another AWS account permission to view the image. ::

    aws imagebuilder put-image-policy \
        --image-arn arn:aws:imagebuilder:us-west-2:123456789012:image/my-example-recipe/1.0.0/1 \
        --policy file://image-policy.json

Contents of ``image-policy.json``::

    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "AWS": "arn:aws:iam::123456789111:root"
                },
                "Action": [
                    "imagebuilder:GetImage",
                    "imagebuilder:ListImages"
                ],
                "Resource": [
                    "arn:aws:imagebuilder:us-west-2:123456789012:image/my-example-recipe/1.0.0/1"
                ]
            }
        ]
    }

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "imageArn": "arn:aws:imagebuilder:us-west-2:123456789012:image/my-example-recipe/1.0.0/1"
    }

For more information, see `Share Image Builder resources with AWS RAM <https://docs.aws.amazon.com/imagebuilder/latest/userguide/manage-shared-resources.html>`__ in the *EC2 Image Builder User Guide*.
