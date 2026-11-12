**To update an image pipeline**

The following ``update-image-pipeline`` example changes the pipeline's schedule to build every day at 6:00 AM UTC. Updates require all of the settings that the pipeline keeps, not just the ones that change. ::

    aws imagebuilder update-image-pipeline \
        --image-pipeline-arn arn:aws:imagebuilder:us-west-2:123456789012:image-pipeline/my-example-pipeline \
        --image-recipe-arn arn:aws:imagebuilder:us-west-2:123456789012:image-recipe/my-example-recipe/1.0.0 \
        --infrastructure-configuration-arn arn:aws:imagebuilder:us-west-2:123456789012:infrastructure-configuration/my-example-infrastructure \
        --schedule 'scheduleExpression=cron(0 6 * * ? *),pipelineExecutionStartCondition=EXPRESSION_MATCH_AND_DEPENDENCY_UPDATES_AVAILABLE' \
        --status ENABLED \
        --client-token a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "imagePipelineArn": "arn:aws:imagebuilder:us-west-2:123456789012:image-pipeline/my-example-pipeline"
    }

For more information, see `Update AMI image pipelines from the AWS CLI <https://docs.aws.amazon.com/imagebuilder/latest/userguide/cli-update-image-pipeline.html>`__ in the *EC2 Image Builder User Guide*.
