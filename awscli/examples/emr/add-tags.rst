**To add tags to a cluster**

The following ``add-tags`` example adds tags to the specified cluster. This command produces no output. ::

    aws emr add-tags \
        --resource-id j-xxxxxxx \
        --tags name="John Doe" age=29 sex=male address="123 East NW Seattle"

To list the tags of the cluster, run the following ``describe-cluster`` command. ::

    aws emr describe-cluster \
        --cluster-id j-xxxxxxx \
        --query Cluster.Tags

Output::

    [
        {
            "Value": "male",
            "Key": "sex"
        },
        {
            "Value": "123 East NW Seattle",
            "Key": "address"
        },
        {
            "Value": "John Doe",
            "Key": "name"
        },
        {
            "Value": "29",
            "Key": "age"
        }
    ]
