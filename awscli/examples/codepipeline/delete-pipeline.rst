**To delete a pipeline**

The following ``delete-pipeline`` example deletes a pipeline named MySecondPipeline from AWS CodePipeline. Use the list-pipelines command to view a list of pipelines associated with your AWS account. This command produces no output. ::

    aws codepipeline delete-pipeline \
        --name MySecondPipeline
