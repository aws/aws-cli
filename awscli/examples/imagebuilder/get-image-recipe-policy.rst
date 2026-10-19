**To get the resource policy for an image recipe**

The following ``get-image-recipe-policy`` example retrieves the resource policy that's applied to the specified image recipe. The ``policy`` property contains the resource-based policy document as a JSON-encoded string. ::

    aws imagebuilder get-image-recipe-policy \
        --image-recipe-arn arn:aws:imagebuilder:us-west-2:123456789012:image-recipe/my-example-recipe/1.0.0

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "policy": "{\"Version\": \"2012-10-17\", \"Statement\": [{\"Effect\": \"Allow\", \"Principal\": {\"AWS\": \"arn:aws:iam::123456789111:root\"}, \"Action\": [\"imagebuilder:GetImageRecipe\", \"imagebuilder:ListImageRecipes\"], \"Resource\": \"arn:aws:imagebuilder:us-west-2:123456789012:image-recipe/my-example-recipe/1.0.0\"}]}"
    }

For more information, see `Share Image Builder resources with AWS RAM <https://docs.aws.amazon.com/imagebuilder/latest/userguide/manage-shared-resources.html>`__ in the *EC2 Image Builder User Guide*.
