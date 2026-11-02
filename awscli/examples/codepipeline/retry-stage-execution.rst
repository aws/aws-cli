**To retry a failed action**

The following ``retry-stage-execution`` example retries a stage that has a failed action. ::

    aws codepipeline retry-stage-execution \
        --pipeline-name MyPipeline \
        --stage-name Deploy \
        --pipeline-execution-id b59babff-5f34-EXAMPLE \
        --retry-mode FAILED_ACTIONS

Output::

    {
        "pipelineExecutionId": "b59babff-5f34-EXAMPLE"
    }

For more information, see `Configuring stage retry for a failed stage or failed actions <https://docs.aws.amazon.com/codepipeline/latest/userguide/stage-retry.html#stage-retry-cli>`__ in the *AWS CodePipeline User Guide*.