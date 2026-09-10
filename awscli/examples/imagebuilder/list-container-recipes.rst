**To list the container recipes that you own**

The following ``list-container-recipes`` example lists the container recipes that your account owns. ::

    aws imagebuilder list-container-recipes \
        --owner Self

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "containerRecipeSummaryList": [
            {
                "arn": "arn:aws:imagebuilder:us-west-2:123456789012:container-recipe/my-example-container-recipe/1.0.0",
                "containerType": "DOCKER",
                "name": "my-example-container-recipe",
                "platform": "Linux",
                "owner": "123456789012",
                "parentImage": "amazonlinux:latest",
                "dateCreated": "2026-09-09T19:31:26.363Z",
                "tags": {}
            }
        ]
    }

For more information, see `List and view container recipe details <https://docs.aws.amazon.com/imagebuilder/latest/userguide/container-recipe-details.html>`__ in the *EC2 Image Builder User Guide*.
