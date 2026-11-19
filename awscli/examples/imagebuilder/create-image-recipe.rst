**Example 1: To create an image recipe**

The following ``create-image-recipe`` example creates an image recipe that applies a custom component on top of the latest Amazon Linux 2023 base image. ::

    aws imagebuilder create-image-recipe \
        --name my-example-recipe \
        --semantic-version 1.0.0 \
        --description "An image recipe that installs my application on Amazon Linux 2023" \
        --parent-image arn:aws:imagebuilder:us-west-2:aws:image/amazon-linux-2023-x86/x.x.x \
        --components componentArn=arn:aws:imagebuilder:us-west-2:123456789012:component/my-example-component/1.0.0/1 \
        --client-token a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "clientToken": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "imageRecipeArn": "arn:aws:imagebuilder:us-west-2:123456789012:image-recipe/my-example-recipe/1.0.0",
        "latestVersionReferences": {
            "latestVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:image-recipe/my-example-recipe/x.x.x",
            "latestMajorVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:image-recipe/my-example-recipe/1.x.x",
            "latestMinorVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:image-recipe/my-example-recipe/1.0.x",
            "latestPatchVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:image-recipe/my-example-recipe/1.0.0"
        }
    }

**Example 2: To create an image recipe with component parameters and block device mappings**

The following ``create-image-recipe`` example creates an image recipe that configures its components and storage. The ``AppVersion`` component parameter selects the application version to install. The block device mapping increases the root volume to an encrypted 30 GiB gp3 volume. ::

    aws imagebuilder create-image-recipe \
        --name my-example-recipe \
        --semantic-version 1.1.0 \
        --description "Installs a specific version of my application on Amazon Linux 2023 with a larger encrypted root volume" \
        --parent-image arn:aws:imagebuilder:us-west-2:aws:image/amazon-linux-2023-x86/x.x.x \
        --components file://components.json \
        --block-device-mappings file://block-device-mappings.json \
        --client-token a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

Contents of ``components.json``::

    [
        {
            "componentArn": "arn:aws:imagebuilder:us-west-2:123456789012:component/my-example-parameterized-component/1.0.0/1",
            "parameters": [
                {
                    "name": "AppVersion",
                    "value": ["2.5.0"]
                }
            ]
        }
    ]

Contents of ``block-device-mappings.json``::

    [
        {
            "deviceName": "/dev/xvda",
            "ebs": {
                "volumeSize": 30,
                "volumeType": "gp3",
                "encrypted": true,
                "deleteOnTermination": true
            }
        }
    ]

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "clientToken": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "imageRecipeArn": "arn:aws:imagebuilder:us-west-2:123456789012:image-recipe/my-example-recipe/1.1.0",
        "latestVersionReferences": {
            "latestVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:image-recipe/my-example-recipe/x.x.x",
            "latestMajorVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:image-recipe/my-example-recipe/1.x.x",
            "latestMinorVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:image-recipe/my-example-recipe/1.1.x",
            "latestPatchVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:image-recipe/my-example-recipe/1.1.0"
        }
    }

For more information, see `Create a new version of an image recipe <https://docs.aws.amazon.com/imagebuilder/latest/userguide/create-image-recipes.html>`__ in the *EC2 Image Builder User Guide*.
