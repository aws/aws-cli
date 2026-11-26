**To share a container recipe with another account**

The following ``put-container-recipe-policy`` example applies a resource policy that grants another AWS account permission to view and use the specified container recipe. ::

    aws imagebuilder put-container-recipe-policy \
        --container-recipe-arn arn:aws:imagebuilder:us-west-2:123456789012:container-recipe/my-example-container-recipe-shared/1.0.0 \
        --policy file://container-recipe-policy.json

Contents of ``container-recipe-policy.json``::

    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowSharedAccountContainerRecipeAccess",
                "Effect": "Allow",
                "Principal": {
                    "AWS": "arn:aws:iam::123456789111:root"
                },
                "Action": [
                    "imagebuilder:GetContainerRecipe",
                    "imagebuilder:ListContainerRecipes"
                ],
                "Resource": "arn:aws:imagebuilder:us-west-2:123456789012:container-recipe/my-example-container-recipe-shared/1.0.0"
            }
        ]
    }

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "containerRecipeArn": "arn:aws:imagebuilder:us-west-2:123456789012:container-recipe/my-example-container-recipe-shared/1.0.0"
    }

For more information, see `Share Image Builder resources with AWS RAM <https://docs.aws.amazon.com/imagebuilder/latest/userguide/manage-shared-resources.html>`__ in the *EC2 Image Builder User Guide*.
