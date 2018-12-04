**To update the container agent on an Amazon ECS container instance**

This example command updates the container agent on the container instance ``a3e98c65-2a40-4452-a63c-62beb4d9be9b`` in the default cluster. 

Command::

  aws ecs update-container-agent --cluster default --container-instance a3e98c65-2a40-4452-a63c-62beb4d9be9b

Output::

  {
      "containerInstance": {
          "status": "ACTIVE",
  ...
          "agentUpdateStatus": "PENDING",
          "versionInfo": {
              "agentVersion": "1.0.0",
              "agentHash": "4023248",
              "dockerVersion": "DockerVersion: 1.5.0"
          }
      }
  }