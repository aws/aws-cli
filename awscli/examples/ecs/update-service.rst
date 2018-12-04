**To change the task definition used in a service**

This example command updates the ``my-http-service`` service to use the ``amazon-ecs-sample`` task definition. 

Command::

  aws ecs update-service --service my-http-service --task-definition amazon-ecs-sample

**To change the number of tasks in a service**

This example command updates the desired count of the ``my-http-service`` service to 10. 

Command::

  aws ecs update-service --service my-http-service --desired-count 10