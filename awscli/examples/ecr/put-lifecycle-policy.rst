**To create a lifecycle policy**

This example creates a lifecycle policy defined by ``policy.json` for a repository called
``project-a/amazon-ecs-sample`` in the default registry for an account.

Command::

  aws ecr put-lifecycle-policy --repository-name "project-a/amazon-ecs-sample" --lifecycle-policy-text "file://policy.json"

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
    "lifecyclePolicyText": "{\"rules\":[{\"rulePriority\":1,\"description\":\"Expire images older than 14 days\",\"selection\":{\"tagStatus\":\"untagged\",\"countType\":\"sinceImagePushed\",\"countUnit\":\"days\",\"countNumber\":14},\"action\":{\"type\":\"expire\"}}]}"
   }
