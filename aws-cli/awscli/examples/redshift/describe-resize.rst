**To describe a resize**

The following ``describe-resize`` example describes the latest resize of a cluster. The request was for 3 nodes of type ``dw.hs1.8xlarge``. ::

    aws redshift describe-resize \
        --cluster-identifier mycluster

Output::

    {
        "Status": "NONE",
        "TargetClusterType": "multi-node",
        "TargetNodeType": "dw.hs1.8xlarge",
        "TargetNumberOfNodes": 3
    }

For more information, see `Resizing a cluster <https://docs.aws.amazon.com/redshift/latest/mgmt/resizing-cluster.html>`__ in the *Amazon Redshift Management Guide*.
