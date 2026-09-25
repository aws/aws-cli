**To import a virtual machine as an Image Builder image**

The following ``import-vm-image`` example registers the output of an EC2 VM Import/Export task (import-ami) as a new Image Builder image, so the imported virtual machine can be used as a base image. ::

    aws imagebuilder import-vm-image \
        --name my-example-imported-image \
        --semantic-version 1.0.0 \
        --platform Linux \
        --os-version "Amazon Linux 2" \
        --vm-import-task-id import-ami-1234567890abcdef0 \
        --client-token a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "clientToken": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "imageArn": "arn:aws:imagebuilder:us-west-2:123456789012:image/my-example-imported-image/1.0.0/1"
    }

For more information, see `Import and export virtual machine images with Image Builder <https://docs.aws.amazon.com/imagebuilder/latest/userguide/vm-import-export.html>`__ in the *EC2 Image Builder User Guide*.
