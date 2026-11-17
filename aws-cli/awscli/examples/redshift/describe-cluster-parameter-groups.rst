**To get a description of all cluster parameter groups**

The following ``describe-cluster-parameter-groups`` example returns a description of all cluster parameter groups for the
account, with column headers.  By default, the output is in JSON format. ::

    aws redshift describe-cluster-parameter-groups

Output::

    {
        "ParameterGroups": [
            {
                "ParameterGroupFamily": "redshift-1.0",
                "Description": "My first cluster parameter group",
                "ParameterGroupName": "myclusterparametergroup"
            }
        ]
    }

You can also obtain the same information in text format using the ``--output text`` option. ::

    aws redshift describe-cluster-parameter-groups \
        --output text

Output::

    redshift-1.0        My first cluster parameter group        myclusterparametergroup

For more information, see `Amazon Redshift parameter groups <https://docs.aws.amazon.com/redshift/latest/mgmt/working-with-parameter-groups.html>`__ in the *Amazon Redshift Management Guide*.
