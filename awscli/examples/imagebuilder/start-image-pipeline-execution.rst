**To start a pipeline build manually**

The following ``start-image-pipeline-execution`` example starts a build for the specified pipeline. The response returns the ARN of the new image build version. ::

    aws imagebuilder start-image-pipeline-execution \
        --image-pipeline-arn arn:aws:imagebuilder:us-west-2:123456789012:image-pipeline/my-example-pipeline \
        --client-token a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "clientToken": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "imageBuildVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:image/my-example-recipe/1.0.0/1"
    }

For more information, see `Run an image pipeline manually <https://docs.aws.amazon.com/imagebuilder/latest/userguide/pipelines-run.html>`__ in the *EC2 Image Builder User Guide*.
