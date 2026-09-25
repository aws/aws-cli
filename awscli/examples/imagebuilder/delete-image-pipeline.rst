**To delete an image pipeline**

The following ``delete-image-pipeline`` example deletes the specified image pipeline. Images that the pipeline created remain in your account. ::

    aws imagebuilder delete-image-pipeline \
        --image-pipeline-arn arn:aws:imagebuilder:us-west-2:123456789012:image-pipeline/my-example-pipeline

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "imagePipelineArn": "arn:aws:imagebuilder:us-west-2:123456789012:image-pipeline/my-example-pipeline"
    }

For more information, see `Delete outdated or unused Image Builder resources <https://docs.aws.amazon.com/imagebuilder/latest/userguide/delete-resources.html>`__ in the *EC2 Image Builder User Guide*.
