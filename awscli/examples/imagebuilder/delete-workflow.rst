**To delete a workflow build version**

The following ``delete-workflow`` example deletes the workflow build version that the ARN specifies. ::

    aws imagebuilder delete-workflow \
        --workflow-build-version-arn arn:aws:imagebuilder:us-west-2:123456789012:workflow/build/my-example-workflow/1.0.0/1

Output::

    {
        "workflowBuildVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:workflow/build/my-example-workflow/1.0.0/1"
    }

For more information, see `Delete outdated or unused Image Builder resources <https://docs.aws.amazon.com/imagebuilder/latest/userguide/delete-resources.html>`__ in the *EC2 Image Builder User Guide*.
