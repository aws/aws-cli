**To list the services in a cluster**

This example command lists the services running in a cluster.

Command::

  aws ecs list-services
  
Output::

  {
      "serviceArns": [
          "arn:aws:ecs:<region>:<aws_account_id>:service/my-http-service"
      ]
  }
