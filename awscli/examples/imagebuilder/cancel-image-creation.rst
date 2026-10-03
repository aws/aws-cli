**To cancel an image build**

The following ``cancel-image-creation`` example cancels a build that is in progress for the specified image build version. ::

    aws imagebuilder cancel-image-creation \
        --image-build-version-arn arn:aws:imagebuilder:us-west-2:123456789012:image/my-example-recipe/1.0.0/1 \
        --client-token a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "clientToken": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "imageBuildVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:image/my-example-recipe/1.0.0/1"
    }

For more information, see `Create custom images with Image Builder <https://docs.aws.amazon.com/imagebuilder/latest/userguide/create-images.html>`__ in the *EC2 Image Builder User Guide*.
