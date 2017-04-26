**To get details of the effective associations for an instance**

This example describes the effective associations for an instance.

Command::

  aws ssm describe-effective-instance-associations --instance-id "i-0000293ffd8c57862"
  
Output::

  {
    "Associations": [
        {
            "InstanceId": "i-0000293ffd8c57862",
            "Content": "{\n    \"schemaVersion\": \"1.2\",\n    \"description\": \"Update the Amazon SSM Agent to the latest version or specified version.\",\n    \"parameters\": {\n        \"version\": {\n            \"default\": \"\",\n            \"description\": \"(Optional) A specific version of the Amazon SSM Agent to install. If not specified, the agent will be updated to the latest version.\",\n            \"type\": \"String\"\n        },\n        \"allowDowngrade\": {\n            \"default\": \"false\",\n            \"description\": \"(Optional) Allow the Amazon SSM Agent service to be downgraded to an earlier version. If set to false, the service can be upgraded to newer versions only (default). If set to true, specify the earlier version.\",\n            \"type\": \"String\",\n            \"allowedValues\": [\n                \"true\",\n                \"false\"\n            ]\n        }\n    },\n    \"runtimeConfig\": {\n        \"aws:updateSsmAgent\": {\n            \"properties\": [\n                {\n                \"agentName\": \"amazon-ssm-agent\",\n                \"source\": \"https://s3.{Region}.amazonaws.com/amazon-ssm-{Region}/ssm-agent-manifest.json\",\n                \"allowDowngrade\": \"{{ allowDowngrade }}\",\n                \"targetVersion\": \"{{ version }}\"\n                }\n            ]\n        }\n    }\n}\n",
            "AssociationId": "d8617c07-2079-4c18-9847-1655fc2698b0"
        }
    ]
  }
