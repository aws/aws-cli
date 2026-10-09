**To get the details of a container recipe**

The following ``get-container-recipe`` example retrieves the details of the specified container recipe, including the components it applies, the Dockerfile template, and the target repository. ::

    aws imagebuilder get-container-recipe \
        --container-recipe-arn arn:aws:imagebuilder:us-west-2:123456789012:container-recipe/my-example-container-recipe/1.0.0

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "containerRecipe": {
            "arn": "arn:aws:imagebuilder:us-west-2:123456789012:container-recipe/my-example-container-recipe/1.0.0",
            "containerType": "DOCKER",
            "name": "my-example-container-recipe",
            "description": "A container recipe that installs my application on Amazon Linux",
            "platform": "Linux",
            "owner": "123456789012",
            "version": "1.0.0",
            "components": [
                {
                    "componentArn": "arn:aws:imagebuilder:us-west-2:123456789012:component/my-example-container-component/1.0.0/1"
                }
            ],
            "dockerfileTemplateData": "FROM {{{ imagebuilder:parentImage }}}\n{{{ imagebuilder:environments }}}\n{{{ imagebuilder:components }}}\n",
            "encrypted": true,
            "parentImage": "amazonlinux:latest",
            "dateCreated": "2026-09-09T19:32:53.983Z",
            "tags": {},
            "targetRepository": {
                "service": "ECR",
                "repositoryName": "my-example-container-repo"
            }
        },
        "latestVersionReferences": {
            "latestVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:container-recipe/my-example-container-recipe/x.x.x",
            "latestMajorVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:container-recipe/my-example-container-recipe/1.x.x",
            "latestMinorVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:container-recipe/my-example-container-recipe/1.0.x",
            "latestPatchVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:container-recipe/my-example-container-recipe/1.0.0"
        }
    }

For more information, see `List and view container recipe details <https://docs.aws.amazon.com/imagebuilder/latest/userguide/container-recipe-details.html>`__ in the *EC2 Image Builder User Guide*.
