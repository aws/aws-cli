**To deregister a container instance from a cluster**

This example deregisters a container instance from the specified cluster in your default region. If there are still tasks running on the container instance, you must either stop those tasks before deregistering, or use the force option.

Command::

  aws ecs deregister-container-instance --cluster default --container-instance <container_instance_UUID> --force