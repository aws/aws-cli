**To promote a cache cluster to the primary role**

This example promotes the cache cluster *mycluster-002* to the primary role for the specified replication group.

Command::

  aws elasticache modify-replication-group --replication-group-id mycluster \
  --primary-cluster-id mycluster-002 --apply-immediately

The nodes of all other cache clusters in the replication group will be read replicas.
If the specified group's *autofailover* is enabled, you cannot mannualy promote cache clusters.
