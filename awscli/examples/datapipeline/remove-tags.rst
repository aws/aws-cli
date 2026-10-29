**To remove a tag from a pipeline**

The following ``remove-tags`` example removes the specified tag from the specified pipeline. ::

    aws datapipeline remove-tags \
        --pipeline-id df-00627471SOVYZEXAMPLE \
        --tag-keys environment

This command produces no output.

For more information, see `Tagging Your Pipeline <https://docs.aws.amazon.com/datapipeline/latest/DeveloperGuide/dp-adding-tags.html>`__ in the *AWS Data Pipeline Developer Guide*.
