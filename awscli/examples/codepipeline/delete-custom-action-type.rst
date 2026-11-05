**To delete a custom action**

The following ``delete-custom-action-type`` example deletes a custom action in AWS CodePipeline by using an already-created JSON file (here named DeleteMyCustomAction.json) that contains the action type, provider name, and version number of the action to be deleted. Use the list-action-types command to view the correct values for category, version, and provider. ::

    aws codepipeline delete-custom-action-type \
        --cli-input-json file://DeleteMyCustomAction.json

Contents of ``DeleteMyCustomAction.json``::

    {
        "category": "Build",
        "version": "1",
        "provider": "MyJenkinsProviderName"
    }

This command produces no output.

For more information, see `Create and add a custom action in CodePipeline <https://docs.aws.amazon.com/codepipeline/latest/userguide/actions-create-custom-action.html>`__ in the *AWS CodePipeline User Guide*.
