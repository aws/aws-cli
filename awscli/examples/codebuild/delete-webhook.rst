**Delete a webhook filter from an AWS CodeBuild project**

The following ``delete-webhook`` example shows how to delete a webhook from a CodeBuild project named ``my-project``. ::

    aws codebuild delete-webhook --project-name my-project

This command produces no output.

For more information, see `Stop Running Builds Automatically (AWS CLI)`_ in the *AWS CodeBuild User Guide*.

.. _`Stop Running Builds Automatically (AWS CLI)`: https://docs.aws.amazon.com/codebuild/latest/userguide/run-build.html#run-build-cli-auto-stop