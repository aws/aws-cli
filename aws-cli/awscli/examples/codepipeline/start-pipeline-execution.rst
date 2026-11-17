**To run the latest revision through a pipeline**

The following ``start-pipeline-execution`` example runs the latest revision present in the source stage of a pipeline through the pipeline named "MyFirstPipeline". ::

    aws codepipeline start-pipeline-execution \
        --name MyFirstPipeline


Output::

    {
        "pipelineExecutionId": "3137f7cb-7cf7-EXAMPLE"
    }

For more information, see `Start a pipeline manually <https://docs.aws.amazon.com/codepipeline/latest/userguide/pipelines-rerun-manually.html>`__ in the *AWS CodePipeline User Guide*.
