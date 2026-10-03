**To share an image recipe with another account**

The following ``put-image-recipe-policy`` example applies a resource policy that grants another AWS account permission to view the specified image recipe. ::

    aws imagebuilder put-image-recipe-policy \
        --image-recipe-arn arn:aws:imagebuilder:us-west-2:123456789012:image-recipe/my-example-recipe/1.0.0 \
        --policy file://image-recipe-policy.json

Contents of ``image-recipe-policy.json``::

    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "AWS": "arn:aws:iam::123456789111:root"
                },
                "Action": [
                    "imagebuilder:GetImageRecipe",
                    "imagebuilder:ListImageRecipes"
                ],
                "Resource": "arn:aws:imagebuilder:us-west-2:123456789012:image-recipe/my-example-recipe/1.0.0"
            }
        ]
    }

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "imageRecipeArn": "arn:aws:imagebuilder:us-west-2:123456789012:image-recipe/my-example-recipe/1.0.0"
    }

For more information, see `Share Image Builder resources with AWS RAM <https://docs.aws.amazon.com/imagebuilder/latest/userguide/manage-shared-resources.html>`__ in the *EC2 Image Builder User Guide*.
