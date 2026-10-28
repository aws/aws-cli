**To deactivate a pipeline**

The following ``deactivate-pipeline`` example deactivates the specified pipeline. This command produces no output. ::

    aws datapipeline deactivate-pipeline \
        --pipeline-id df-00627471SOVYZEXAMPLE

To deactivate the pipeline only after all running activities finish, use the following command. ::

    aws datapipeline deactivate-pipeline \
        --pipeline-id df-00627471SOVYZEXAMPLE \
        --no-cancel-active
