**To delete a pipeline**

The following ``delete-pipeline`` example deletes a pipeline named MySecondPipeline from AWS CodePipeline. Use the list-pipelines command to view a list of pipelines associated with your AWS account. ::

    aws codepipeline delete-pipeline \
        --name MySecondPipeline

This command produces no output.

For more information, see `Delete a pipeline in CodePipeline <https://docs.aws.amazon.com/codepipeline/latest/userguide/pipelines-delete.html>`__ in the *AWS CodePipeline User Guide*.
