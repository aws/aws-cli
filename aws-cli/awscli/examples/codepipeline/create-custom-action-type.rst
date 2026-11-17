**To create a custom action**

The following ``create-custom-action-type`` example creates a custom action for AWS CodePipeline using an already-created JSON file (here named MyCustomAction.json) that contains the structure of the custom action. ::

    aws codepipeline create-custom-action-type \
        --cli-input-json file://MyCustomAction.json

Contents of ``MyCustomAction.json``::

    {
        "category": "Build",
        "provider": "MyJenkinsProviderName",
        "version": "1",
        "settings": {
            "entityUrlTemplate": "https://192.0.2.4/job/{Config:ProjectName}/",
            "executionUrlTemplate": "https://192.0.2.4/job/{Config:ProjectName}/lastSuccessfulBuild/{ExternalExecutionId}/"
        },
        "configurationProperties": [
            {
                "name": "MyJenkinsExampleBuildProject",
                "required": true,
                "key": true,
                "secret": false,
                "queryable": false,
                "description": "The name of the build project must be provided when this action is added to the pipeline.",
                "type": "String"
            }
        ],
        "inputArtifactDetails": {
            "maximumCount": 1,
            "minimumCount": 0
        },
        "outputArtifactDetails": {
            "maximumCount": 1,
            "minimumCount": 0
        }
    }

This command returns the structure of the custom action.

Output::

    {
        "actionType": {
            "id": {
                "category": "Build",
                "owner": "Custom",
                "provider": "MyJenkinsProviderName",
                "version": "1"
            },
            "settings": {
                "entityUrlTemplate": "https://192.0.2.4/job/{Config:ProjectName}/",
                "executionUrlTemplate": "https://192.0.2.4/job/{Config:ProjectName}/lastSuccessfulBuild/{ExternalExecutionId}/"
            },
            "actionConfigurationProperties": [
                {
                    "name": "MyJenkinsExampleBuildProject",
                    "required": true,
                    "key": true,
                    "secret": false,
                    "queryable": false,
                    "description": "The name of the build project must be provided when this action is added to the pipeline.",
                    "type": "String"
                }
            ],
            "inputArtifactDetails": {
                "minimumCount": 0,
                "maximumCount": 1
            },
            "outputArtifactDetails": {
                "minimumCount": 0,
                "maximumCount": 1
            }
        }
    }

For more information, see `Create and add a custom action in CodePipeline <https://docs.aws.amazon.com/codepipeline/latest/userguide/actions-create-custom-action.html>`__ in the *AWS CodePipeline User Guide*.
