**To create a lifecycle policy preview**

This example creates a lifecycle policy preview defined by ``policy.json` for a repository called
``project-a/amazon-ecs-sample`` in the default registry for an account.

Command::

  aws ecr start-lifecycle-policy-preview --repository-name "project-a/amazon-ecs-sample" --lifecycle-policy-text "file://policy.json"

JSON file format::

   {
       "rules": [
           {
               "rulePriority": 1,
               "description": "Expire images older than 14 days",
               "selection": {
                   "tagStatus": "untagged",
                   "countType": "sinceImagePushed",
                   "countUnit": "days",
                   "countNumber": 14
               },
               "action": {
                   "type": "expire"
               }
           }
       ]
   }

Output::

   {
       "registryId": "<aws_account_id>",
       "repositoryName": "project-a/amazon-ecs-sample",
       "lifecyclePolicyText": "{\n    \"rules\": [\n        {\n            \"rulePriority\": 1,\n            \"description\": \"Expire images older than 14 days\",\n            \"selection\": {\n                \"tagStatus\": \"untagged\",\n                \"countType\": \"sinceImagePushed\",\n                \"countUnit\": \"days\",\n                \"countNumber\": 14\n            },\n            \"action\": {\n                \"type\": \"expire\"\n            }\n        }\n    ]\n}\n",
       "status": "IN_PROGRESS"
  }
