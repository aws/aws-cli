**To get the policy attached to a container recipe**

The following ``get-container-recipe-policy`` example retrieves the resource policy for a container recipe that you shared with another AWS account. The ``policy`` property contains the resource-based policy document as a JSON-encoded string. ::

    aws imagebuilder get-container-recipe-policy \
        --container-recipe-arn arn:aws:imagebuilder:us-west-2:123456789012:container-recipe/my-example-container-recipe-shared/1.0.0

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "policy": "{\"Version\": \"2012-10-17\", \"Statement\": [{\"Sid\": \"AllowSharedAccountContainerRecipeAccess\", \"Effect\": \"Allow\", \"Principal\": {\"AWS\": \"arn:aws:iam::123456789111:root\"}, \"Action\": [\"imagebuilder:GetContainerRecipe\", \"imagebuilder:ListContainerRecipes\"], \"Resource\": \"arn:aws:imagebuilder:us-west-2:123456789012:container-recipe/my-example-container-recipe-shared/1.0.0\"}]}"
    }

For more information, see `Share Image Builder resources with AWS RAM <https://docs.aws.amazon.com/imagebuilder/latest/userguide/manage-shared-resources.html>`__ in the *EC2 Image Builder User Guide*.
