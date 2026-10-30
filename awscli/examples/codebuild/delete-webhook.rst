**To delete a webhook filter from an AWS CodeBuild project**

The following ``delete-webhook`` example deletes a webhook from the specified CodeBuild project. ::

    aws codebuild delete-webhook \
        --project-name my-project
    
This command produces no output.

For more information, see `Use webhooks with AWS CodeBuild <https://docs.aws.amazon.com/codebuild/latest/userguide/webhooks.html>`__ in the *AWS CodeBuild User Guide*.
