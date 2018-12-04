**To delete a service**

This example command deletes the ``my-http-service`` service. The service must have a desired count and running count of 0 before you can delete it.

Command::

  aws ecs delete-service --service my-http-service

