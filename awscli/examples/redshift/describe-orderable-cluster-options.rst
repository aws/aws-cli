**To describe all orderable cluster options**

The following ``describe-orderable-cluster-options`` example returns descriptions of all orderable cluster options. By default, the output is in JSON format. ::

    aws redshift describe-orderable-cluster-options

Output::

    {
        "OrderableClusterOptions": [
            {
                "NodeType": "dw.hs1.8xlarge",
                "AvailabilityZones": [
                    { "Name": "us-east-1a" },
                    { "Name": "us-east-1b" },
                    { "Name": "us-east-1c" } ],
                "ClusterVersion": "1.0",
                "ClusterType": "multi-node"
            },
            {
                "NodeType": "dw.hs1.xlarge",
                "AvailabilityZones": [
                    { "Name": "us-east-1a" },
                    { "Name": "us-east-1b" },
                    { "Name": "us-east-1c" } ],
                "ClusterVersion": "1.0",
                "ClusterType": "multi-node"
            },
            {
                "NodeType": "dw.hs1.xlarge",
                "AvailabilityZones": [
                    { "Name": "us-east-1a" },
                    { "Name": "us-east-1b" },
                    { "Name": "us-east-1c" } ],
                "ClusterVersion": "1.0",
                "ClusterType": "single-node"
            } ]
    }

You can also obtain the same information in text format using the ``--output text`` option. ::

    aws redshift describe-orderable-cluster-options \
        --output text

Output::

    dw.hs1.8xlarge      1.0     multi-node
    us-east-1a
    us-east-1b
    us-east-1c
    dw.hs1.xlarge       1.0     multi-node
    us-east-1a
    us-east-1b
    us-east-1c
    dw.hs1.xlarge       1.0     single-node
    us-east-1a
    us-east-1b
    us-east-1c


