**To create a pipeline**

The following ``create-pipeline`` example creates a pipeline. ::

    aws datapipeline create-pipeline \
        --name my-pipeline \
        --unique-id my-pipeline-token
   
Output::

    {
        "pipelineId": "df-00627471SOVYZEXAMPLE"
    }

For more information, see `Creating a pipeline <https://docs.aws.amazon.com/datapipeline/latest/DeveloperGuide/dp-creating-pipelines.html>`__ in the *AWS Data Pipeline Developer Guide*.
