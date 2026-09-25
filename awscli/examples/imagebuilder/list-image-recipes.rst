**To list the image recipes that you own**

The following ``list-image-recipes`` example lists the image recipes that your account owns. ::

    aws imagebuilder list-image-recipes \
        --owner Self

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "imageRecipeSummaryList": [
            {
                "arn": "arn:aws:imagebuilder:us-west-2:123456789012:image-recipe/my-example-linux-recipe/1.0.0",
                "name": "my-example-linux-recipe",
                "platform": "Linux",
                "owner": "123456789012",
                "parentImage": "arn:aws:imagebuilder:us-west-2:aws:image/amazon-linux-2023-x86/x.x.x",
                "dateCreated": "2026-09-09T19:30:33.064Z",
                "tags": {}
            },
            {
                "arn": "arn:aws:imagebuilder:us-west-2:123456789012:image-recipe/my-example-windows-recipe/1.0.0",
                "name": "my-example-windows-recipe",
                "platform": "Windows",
                "owner": "123456789012",
                "parentImage": "arn:aws:imagebuilder:us-west-2:aws:image/windows-server-2022-english-full-base-x86/x.x.x",
                "dateCreated": "2026-09-09T19:30:35.110Z",
                "tags": {}
            }
        ]
    }

For more information, see `List and view image recipe details <https://docs.aws.amazon.com/imagebuilder/latest/userguide/image-recipe-details.html>`__ in the *EC2 Image Builder User Guide*.
