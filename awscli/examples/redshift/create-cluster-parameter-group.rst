**To create a cluster parameter group**

The following ``create-cluster-parameter-group`` example creates a new cluster parameter group. ::

    aws redshift create-cluster-parameter-group \
        --parameter-group-name myclusterparametergroup \
        --parameter-group-family redshift-1.0 \
        --description "My first cluster parameter group"

Output::

    {
        "ClusterParameterGroup": {
            "ParameterGroupFamily": "redshift-1.0",
            "Description": "My first cluster parameter group",
            "ParameterGroupName": "myclusterparametergroup"
        }
    }

For more information, see `Amazon Redshift parameter groups <https://docs.aws.amazon.com/redshift/latest/mgmt/working-with-parameter-groups.html>`__ in the *Amazon Redshift Management Guide*.
