**To import a Windows 11 ISO disk image**

The following ``import-disk-image`` example starts an image build that converts a Windows 11 ISO disk file stored in Amazon S3 into an AMI. The ``imageBuildVersionArn`` in the response identifies the Image Builder image resource that tracks the build, not the output AMI. ::

    aws imagebuilder import-disk-image \
        --name my-example-imported-image \
        --semantic-version 1.0.0 \
        --platform Windows \
        --os-version "Microsoft Windows 11" \
        --uri s3://amzn-s3-demo-bucket/Win11_23H2_English_x64.iso \
        --infrastructure-configuration-arn arn:aws:imagebuilder:us-west-2:123456789012:infrastructure-configuration/my-example-infrastructure \
        --client-token a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

Output::

    {
        "clientToken": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "imageBuildVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:image/my-example-imported-image/1.0.0/1"
    }

For more information, see `Import verified Windows ISO disk images with Image Builder <https://docs.aws.amazon.com/imagebuilder/latest/userguide/import-iso-disk.html>`__ in the *EC2 Image Builder User Guide*.
