**To retrieve a lifecycle policy**

This example retrieves the lifecycle policy for a repository called ``project-a/amazon-ecs-sample`` in the default registry for an account.

Command::

  aws ecr get-lifecycle-policy --repository-name "project-a/amazon-ecs-sample"

Output::

   {
       "registryId": "<aws_account_id>",
       "repositoryName": "project-a/amazon-ecs-sample",
       "lifecyclePolicyText": "{\"rules\":[{\"rulePriority\":1,\"description\":\"Expire images older than 14 days\",\"selection\":{\"tagStatus\":\"untagged\",\"countType\":\"sinceImagePushed\",\"countUnit\":\"days\",\"countNumber\":14},\"action\":{\"type\":\"expire\"}}]}",
       "lastEvaluatedAt": 1504295007.0
   }
