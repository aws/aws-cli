**Example 1: To create an image pipeline**

The following ``create-image-pipeline`` example creates a pipeline that builds a new image version every Sunday at 9:00 AM UTC, if the base image or components have updates. ::

    aws imagebuilder create-image-pipeline \
        --name my-example-pipeline \
        --description "Builds a new version of my image every Sunday" \
        --image-recipe-arn arn:aws:imagebuilder:us-west-2:123456789012:image-recipe/my-example-recipe/1.0.0 \
        --infrastructure-configuration-arn arn:aws:imagebuilder:us-west-2:123456789012:infrastructure-configuration/my-example-infrastructure \
        --distribution-configuration-arn arn:aws:imagebuilder:us-west-2:123456789012:distribution-configuration/my-example-distribution \
        --schedule 'scheduleExpression=cron(0 9 ? * SUN *),pipelineExecutionStartCondition=EXPRESSION_MATCH_AND_DEPENDENCY_UPDATES_AVAILABLE' \
        --status ENABLED \
        --client-token a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "clientToken": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "imagePipelineArn": "arn:aws:imagebuilder:us-west-2:123456789012:image-pipeline/my-example-pipeline"
    }

**Example 2: To create an image pipeline with scanning, custom workflows, and an auto-disable policy**

The following ``create-image-pipeline`` example creates a pipeline that uses your custom build workflow and enables image scanning. The schedule evaluates its cron expression in the America/Los_Angeles time zone. The auto-disable policy disables the pipeline after 3 consecutive failed scheduled builds. ::

    aws imagebuilder create-image-pipeline \
        --name my-example-pipeline \
        --description "Builds a scanned image with my custom build workflow on Sunday mornings when dependency updates are available" \
        --image-recipe-arn arn:aws:imagebuilder:us-west-2:123456789012:image-recipe/my-example-recipe/1.1.0 \
        --infrastructure-configuration-arn arn:aws:imagebuilder:us-west-2:123456789012:infrastructure-configuration/my-example-infrastructure \
        --distribution-configuration-arn arn:aws:imagebuilder:us-west-2:123456789012:distribution-configuration/my-example-distribution \
        --workflows workflowArn=arn:aws:imagebuilder:us-west-2:123456789012:workflow/build/my-example-workflow/1.0.0/1 \
        --execution-role arn:aws:iam::123456789012:role/aws-service-role/imagebuilder.amazonaws.com/AWSServiceRoleForImageBuilder \
        --image-scanning-configuration imageScanningEnabled=true \
        --schedule file://schedule.json \
        --status ENABLED \
        --client-token a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

Contents of ``schedule.json``::

    {
        "scheduleExpression": "cron(0 9 ? * SUN *)",
        "timezone": "America/Los_Angeles",
        "pipelineExecutionStartCondition": "EXPRESSION_MATCH_AND_DEPENDENCY_UPDATES_AVAILABLE",
        "autoDisablePolicy": {
            "failureCount": 3
        }
    }

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "clientToken": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "imagePipelineArn": "arn:aws:imagebuilder:us-west-2:123456789012:image-pipeline/my-example-pipeline"
    }

For more information, see `Create an AMI image pipeline from the AWS CLI <https://docs.aws.amazon.com/imagebuilder/latest/userguide/cli-create-image-pipeline.html>`__ in the *EC2 Image Builder User Guide*.
