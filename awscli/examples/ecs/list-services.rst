**To list the services in a cluster**

The following example shows how to list the services running in a cluster.

Command::

  aws ecs list-services --cluster MyCluster
  
Output::

  {
      "serviceArns": [
          "arn:aws:ecs:us-west-2:123456789012:service/MyCluster/MyService"
      ]
  }
