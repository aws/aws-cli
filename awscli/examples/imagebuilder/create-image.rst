**Example 1: To create an image**

The following ``create-image`` example creates a new image from the specified image recipe and infrastructure configuration. ::

    aws imagebuilder create-image \
        --image-recipe-arn arn:aws:imagebuilder:us-west-2:123456789012:image-recipe/my-example-recipe/1.0.0 \
        --infrastructure-configuration-arn arn:aws:imagebuilder:us-west-2:123456789012:infrastructure-configuration/my-example-infrastructure \
        --client-token a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "clientToken": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "imageBuildVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:image/my-example-recipe/1.0.0/1",
        "latestVersionReferences": {
            "latestVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:image/my-example-recipe/x.x.x",
            "latestMajorVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:image/my-example-recipe/1.x.x",
            "latestMinorVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:image/my-example-recipe/1.0.x",
            "latestPatchVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:image/my-example-recipe/1.0.0"
        }
    }

**Example 2: To create an image with custom build and parallel test workflows**

The following ``create-image`` example creates an image that uses your custom build and test workflows. It uses the Image Builder service-linked role as the execution role. Both test workflows are in the same parallel group, so they can run at the same time after the build workflow completes. ::

    aws imagebuilder create-image \
        --image-recipe-arn arn:aws:imagebuilder:us-west-2:123456789012:image-recipe/my-example-recipe/1.0.0 \
        --infrastructure-configuration-arn arn:aws:imagebuilder:us-west-2:123456789012:infrastructure-configuration/my-example-infrastructure \
        --workflows file://workflows.json \
        --execution-role arn:aws:iam::123456789012:role/aws-service-role/imagebuilder.amazonaws.com/AWSServiceRoleForImageBuilder \
        --client-token a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

Contents of ``workflows.json``::

    [
        {
            "workflowArn": "arn:aws:imagebuilder:us-west-2:123456789012:workflow/build/my-example-workflow/1.0.0/1"
        },
        {
            "workflowArn": "arn:aws:imagebuilder:us-west-2:123456789012:workflow/test/my-example-integration-tests/1.0.0/1",
            "parallelGroup": "post-build-tests"
        },
        {
            "workflowArn": "arn:aws:imagebuilder:us-west-2:123456789012:workflow/test/my-example-compliance-tests/1.0.0/1",
            "parallelGroup": "post-build-tests"
        }
    ]

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "clientToken": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "imageBuildVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:image/my-example-recipe/1.0.0/1",
        "latestVersionReferences": {
            "latestVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:image/my-example-recipe/x.x.x",
            "latestMajorVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:image/my-example-recipe/1.x.x",
            "latestMinorVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:image/my-example-recipe/1.0.x",
            "latestPatchVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:image/my-example-recipe/1.0.0"
        }
    }

For more information, see `Create custom images with Image Builder <https://docs.aws.amazon.com/imagebuilder/latest/userguide/create-images.html>`__ in the *EC2 Image Builder User Guide*.
