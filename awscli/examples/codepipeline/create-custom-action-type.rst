**To create a custom action**

This example creates a custom action for AWS CodePipeline using an already-created JSON file (here named MyCustomAction.json) that contains the structure of the custom action. For more information about the requirements for creating a custom action, including the structure of the file, see the AWS CodePipeline User Guide.

Command::

  aws codepipeline create-custom-action-type --cli-input-json file://MyCustomAction.json
  
JSON file sample contents::
  
  {
   "actionType": {
    "actionConfigurationProperties": [
      {
        "description": "The name of the build project must be provided when this action is added to the pipeline.",
        "key": true,
        "name": "MyJenkinsExampleBuildProject",
        "queryable": false,
        "required": true,
        "secret": false
      }
    ],
    "id": {
      "__type": "ActionTypeId",
      "category": "Build",
      "owner": "Custom",
      "provider": "MyJenkinsProviderName",
      "version": "1"
    },
    "inputArtifactDetails": {
      "maximumCount": 1,
      "minimumCount": 0
    },
    "outputArtifactDetails": {
      "maximumCount": 1,
      "minimumCount": 0
    },
    "settings": {
      "entityUrlTemplate": "https://192.0.2.4/job/{Config:ProjectName}/",
      "executionUrlTemplate": "https://192.0.2.4/job/{Config:ProjectName}/lastSuccessfulBuild/{ExternalExecutionId}/"
    }
   }
  }

Output::

  This command returns the structure of the custom action.