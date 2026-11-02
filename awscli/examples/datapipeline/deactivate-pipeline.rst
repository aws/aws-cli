**To deactivate a pipeline**

The following ``deactivate-pipeline`` example deactivates the specified pipeline. ::

    aws datapipeline deactivate-pipeline \
        --pipeline-id df-00627471SOVYZEXAMPLE

This command produces no output.

To deactivate the pipeline only after all running activities finish, use the following command. ::

    aws datapipeline deactivate-pipeline \
        --pipeline-id df-00627471SOVYZEXAMPLE \
        --no-cancel-active

For more information, see `Deactivating Your Pipeline <https://docs.aws.amazon.com/datapipeline/latest/DeveloperGuide/dp-deactivate-pipeline.html>`__ in the *AWS Data Pipeline Developer Guide*.
