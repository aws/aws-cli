**To create an Amazon ElastiCache Replication Group**

The following ``create-replication-group`` command launches a new Amazon ElastiCache Redis replication group::

    aws elasticache create-replication-group --replication-group-id myRedis \
    --replication-group-description "desc of myRedis" \
    --automatic-failover-enabled --num-cache-clusters 3 \
    --cache-node-type cache.m3.medium \
    --engine redis --engine-version 2.8.24 \
    --cache-parameter-group-name default.redis2.8 \
    --cache-subnet-group-name default --security-group-ids sg-12345678 

In the preceding example, the replication group is created with 3 clusters(primary plus 2 replicas) and has a cache node class of cach3.m3.medium.
With `--automatic-failover-enabled` option, Multi-AZ and automatic failover are enabled.
    
This command output a JSON block that indicates that the replication group was created.
