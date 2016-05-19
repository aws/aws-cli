**To modify cache parameter groups**

This example modifies parameters for the specified cache parameter group.

Command::

  aws elasticache modify-cache-parameter-group \
  --cache-parameter-group-name my-redis-28 --parameter-name-values \
  ParameterName=close-on-slave-write,ParameterValue=no \
  ParameterName=timeout,ParameterValue=60

Output::

  {
      "CacheParameterGroupName": "my-redis-28"
  }

