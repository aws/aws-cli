**To deregister a task definition**

This example deregisters the first revision of the ``curler`` task definition in your default region. Note that in the resulting output, the task definition status becomes ``INACTIVE``.

Command::

  aws ecs deregister-task-definition --task-definition curler:1

Output::

  {
      "taskDefinition": {
          "status": "INACTIVE",
          "family": "curler",
          "volumes": [],
          "taskDefinitionArn": "arn:aws:ecs:us-west-2:<aws_account_id>:task-definition/curler:1",
          "containerDefinitions": [
              {
                  "environment": [],
                  "name": "curler",
                  "mountPoints": [],
                  "image": "curl:latest",
                  "cpu": 100,
                  "portMappings": [],
                  "entryPoint": [],
                  "memory": 256,
                  "command": [
                      "curl -v http://example.com/"
                  ],
                  "essential": true,
                  "volumesFrom": []
              }
          ],
          "revision": 1
      }
  }