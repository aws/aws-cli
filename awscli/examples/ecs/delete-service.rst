**To delete a service**

The following example shows how to delete a service. Using the force parameter allows you to delete a service even if it has not been scaled to zero tasks.

Command::

  aws ecs delete-service --cluster MyCluster --service MyService1 --force
