**Example 1: To create a container recipe**

The following ``create-container-recipe`` example creates a Docker container recipe that applies one build component, using the latest Amazon Linux container image as the parent and an existing Amazon ECR repository as the target. ::

    aws imagebuilder create-container-recipe \
        --container-type DOCKER \
        --name my-example-container-recipe \
        --semantic-version 1.0.0 \
        --parent-image amazonlinux:latest \
        --components componentArn=arn:aws:imagebuilder:us-west-2:123456789012:component/my-example-container-component/1.0.0/1 \
        --dockerfile-template-data file://dockerfile-template.txt \
        --target-repository service=ECR,repositoryName=my-example-container-repo \
        --client-token a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

Contents of ``dockerfile-template.txt``::

    FROM {{{ imagebuilder:parentImage }}}
    {{{ imagebuilder:environments }}}
    {{{ imagebuilder:components }}}

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "clientToken": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "containerRecipeArn": "arn:aws:imagebuilder:us-west-2:123456789012:container-recipe/my-example-container-recipe/1.0.0",
        "latestVersionReferences": {
            "latestVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:container-recipe/my-example-container-recipe/x.x.x",
            "latestMajorVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:container-recipe/my-example-container-recipe/1.x.x",
            "latestMinorVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:container-recipe/my-example-container-recipe/1.0.x",
            "latestPatchVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:container-recipe/my-example-container-recipe/1.0.0"
        }
    }

**Example 2: To create a container recipe with a custom build instance configuration**

The following ``create-container-recipe`` example creates a container recipe that customizes the Amazon EC2 instance that builds the container image. The build instance launches from an Amazon ECS-optimized instance image and uses a 40 GiB gp3 volume. ::

    aws imagebuilder create-container-recipe \
        --container-type DOCKER \
        --name my-example-container-recipe \
        --semantic-version 1.1.0 \
        --description "A container recipe that builds on an ECS-optimized instance image with a larger build volume" \
        --parent-image amazonlinux:latest \
        --components componentArn=arn:aws:imagebuilder:us-west-2:123456789012:component/my-example-container-component/1.0.0/1 \
        --instance-configuration file://instance-configuration.json \
        --dockerfile-template-data file://dockerfile-template.txt \
        --target-repository service=ECR,repositoryName=my-example-container-repo \
        --client-token a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

Contents of ``instance-configuration.json``::

    {
        "image": "ami-1234567890abcdef0",
        "blockDeviceMappings": [
            {
                "deviceName": "/dev/xvda",
                "ebs": {
                    "volumeSize": 40,
                    "volumeType": "gp3",
                    "deleteOnTermination": true
                }
            }
        ]
    }

Contents of ``dockerfile-template.txt``::

    FROM {{{ imagebuilder:parentImage }}}
    {{{ imagebuilder:environments }}}
    {{{ imagebuilder:components }}}

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "clientToken": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "containerRecipeArn": "arn:aws:imagebuilder:us-west-2:123456789012:container-recipe/my-example-container-recipe/1.1.0",
        "latestVersionReferences": {
            "latestVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:container-recipe/my-example-container-recipe/x.x.x",
            "latestMajorVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:container-recipe/my-example-container-recipe/1.x.x",
            "latestMinorVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:container-recipe/my-example-container-recipe/1.1.x",
            "latestPatchVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:container-recipe/my-example-container-recipe/1.1.0"
        }
    }

For more information, see `Create a new version of a container recipe <https://docs.aws.amazon.com/imagebuilder/latest/userguide/create-container-recipes.html>`__ in the *EC2 Image Builder User Guide*.
