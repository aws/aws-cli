**To delete a container recipe**

The following ``delete-container-recipe`` example deletes the specified container recipe version. ::

    aws imagebuilder delete-container-recipe \
        --container-recipe-arn arn:aws:imagebuilder:us-west-2:123456789012:container-recipe/my-example-container-recipe/1.0.0

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "containerRecipeArn": "arn:aws:imagebuilder:us-west-2:123456789012:container-recipe/my-example-container-recipe/1.0.0"
    }

For more information, see `Delete outdated or unused Image Builder resources <https://docs.aws.amazon.com/imagebuilder/latest/userguide/delete-resources.html>`__ in the *EC2 Image Builder User Guide*.
