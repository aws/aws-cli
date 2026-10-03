**To get the details of an image recipe**

The following ``get-image-recipe`` example retrieves the full definition of an image recipe, including the components it applies and the base image it builds on. ::

    aws imagebuilder get-image-recipe \
        --image-recipe-arn arn:aws:imagebuilder:us-west-2:123456789012:image-recipe/my-example-app-recipe/1.0.0

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "imageRecipe": {
            "arn": "arn:aws:imagebuilder:us-west-2:123456789012:image-recipe/my-example-app-recipe/1.0.0",
            "name": "my-example-app-recipe",
            "description": "An image recipe that installs my application on Amazon Linux 2023",
            "platform": "Linux",
            "owner": "123456789012",
            "version": "1.0.0",
            "components": [
                {
                    "componentArn": "arn:aws:imagebuilder:us-west-2:123456789012:component/my-example-app/1.0.0/1"
                }
            ],
            "parentImage": "arn:aws:imagebuilder:us-west-2:aws:image/amazon-linux-2023-x86/x.x.x",
            "dateCreated": "2026-09-09T19:30:21.183Z",
            "tags": {},
            "workingDirectory": "/tmp"
        },
        "latestVersionReferences": {
            "latestVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:image-recipe/my-example-app-recipe/x.x.x",
            "latestMajorVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:image-recipe/my-example-app-recipe/1.x.x",
            "latestMinorVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:image-recipe/my-example-app-recipe/1.0.x",
            "latestPatchVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:image-recipe/my-example-app-recipe/1.0.0"
        }
    }

For more information, see `List and view image recipe details <https://docs.aws.amazon.com/imagebuilder/latest/userguide/image-recipe-details.html>`__ in the *EC2 Image Builder User Guide*.
