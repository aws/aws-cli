**To add a tag to a pipeline**

The following ``add-tags`` example adds the specified tag to the specified pipeline. ::

    aws datapipeline add-tags \
        --pipeline-id df-00627471SOVYZEXAMPLE \
        --tags key=environment,value=production key=owner,value=sales

This command produces no output.
   
To view the tags, use the describe-pipelines command. For example, the tags added in the example command appear as follows in the output for describe-pipelines::

    {
        ...
            "tags": [
                {
                    "value": "production",
                    "key": "environment"
                },
                {
                    "value": "sales",
                    "key": "owner"
                }
            ]
        ...
    }

For more information, see `Tagging Your Pipeline <https://docs.aws.amazon.com/datapipeline/latest/DeveloperGuide/dp-adding-tags.html>`__ in the *AWS Data Pipeline Developer Guide*.
