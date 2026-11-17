**To view the action types available**

The following ``list-action-types`` example uses the ``--action-owner-filter`` option to return only custom actions. Used by itself, the ``list-action-types`` command returns the structure of all actions available to your AWS account. ::

    aws codepipeline list-action-types \
        --action-owner-filter Custom


Output::

    {
        "actionTypes": [
            {
                "inputArtifactDetails": {
                    "maximumCount": 5,
                    "minimumCount": 0
                },
                "actionConfigurationProperties": [
                    {
                        "secret": false,
                        "required": true,
                        "name": "MyJenkinsExampleBuildProject",
                        "key": true,
                        "queryable": true
                    }
                ],
                "outputArtifactDetails": {
                    "maximumCount": 5,
                    "minimumCount": 0
                },
                "id": {
                    "category": "Build",
                    "owner": "Custom",
                    "version": "1",
                    "provider": "MyJenkinsProviderName"
                },
                "settings": {
                    "entityUrlTemplate": "http://192.0.2.4/job/{Config:ProjectName}",
                    "executionUrlTemplate": "http://192.0.2.4/job/{Config:ProjectName}/{ExternalExecutionId}"
                }
            },
            {
                "inputArtifactDetails": {
                    "maximumCount": 5,
                    "minimumCount": 0
                },
                "actionConfigurationProperties": [
                    {
                        "secret": false,
                        "required": true,
                        "name": "MyJenkinsExampleTestProject",
                        "key": true,
                        "queryable": true
                    }
                ],
                "outputArtifactDetails": {
                    "maximumCount": 5,
                    "minimumCount": 0
                },
                "id": {
                    "category": "Test",
                    "owner": "Custom",
                    "version": "1",
                    "provider": "MyJenkinsProviderName"
                },
                "settings": {
                    "entityUrlTemplate": "http://192.0.2.4/job/{Config:ProjectName}",
                    "executionUrlTemplate": "http://192.0.2.4/job/{Config:ProjectName}/{ExternalExecutionId}"
                }
            }
        ]
    }

For more information, see `Use action types, custom actions, and approval actions <https://docs.aws.amazon.com/codepipeline/latest/userguide/actions.html>`__ in the *AWS CodePipeline User Guide*.
