**To describe a service**

This example command provides descriptive information about the ``my-http-service``.

Command::

  aws ecs describe-services --service my-http-service
  
Output::

  {
      "services": [
          {
              "status": "ACTIVE", 
              "taskDefinition": "arn:aws:ecs:<region>:<aws_account_id>:task-definition/amazon-ecs-sample:1", 
              "pendingCount": 0, 
              "loadBalancers": [], 
              "desiredCount": 10, 
              "serviceName": "my-http-service", 
              "clusterArn": "arn:aws:ecs:<region>:<aws_account_id>:cluster/default", 
              "serviceArn": "arn:aws:ecs:<region>:<aws_account_id>:service/my-http-service", 
              "deployments": [
                  {
                      "status": "PRIMARY", 
                      "pendingCount": 0, 
                      "createdAt": 1428326312.703, 
                      "desiredCount": 10, 
                      "taskDefinition": "arn:aws:ecs:<region>:<aws_account_id>:task-definition/amazon-ecs-sample:1", 
                      "updatedAt": 1428326312.703, 
                      "id": "ecs-svc/9223370608528463088", 
                      "runningCount": 10
                  }
              ], 
              "events": [
                  {
                      "message": "(service my-http-service) has reached a steady state.", 
                      "id": "97c8a8e0-16a5-4d30-80bd-9e5413f8951b", 
                      "createdAt": 1428326587.208
                  }
              ], 
              "runningCount": 10
          }
      ], 
      "failures": []
  }
