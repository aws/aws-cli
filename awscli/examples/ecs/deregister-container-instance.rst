**To deregister a container instance from a cluster**

The following example shows how to deregister a container instance from a cluster. If there are still tasks running on the container instance, you must either stop those tasks before deregistering, or use the force option.

Command::

  aws ecs deregister-container-instance --cluster default --container-instance <container_instance_UUID> --force