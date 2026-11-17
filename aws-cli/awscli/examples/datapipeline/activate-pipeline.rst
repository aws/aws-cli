**To activate a pipeline**

The following ``activate-pipeline`` example activates the specified pipeline. ::

    aws datapipeline activate-pipeline \
        --pipeline-id df-00627471SOVYZEXAMPLE

This command produces no output.

To activate the pipeline at a specific date and time, use the following command. ::

    aws datapipeline activate-pipeline \
        --pipeline-id df-00627471SOVYZEXAMPLE \
        --start-timestamp 2015-04-07T00:00:00Z

For more information, see `Working with pipelines <https://docs.aws.amazon.com/datapipeline/latest/DeveloperGuide/dp-managing-pipeline.html>`__ in the *AWS Data Pipeline Developer Guide*.
