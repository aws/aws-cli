**To reset parameters in a parameter group**

The following ``reset-cluster-parameter-group`` example resets all of the parameters in a parameter group. ::

    aws redshift reset-cluster-parameter-group \
        --parameter-group-name myclusterparametergroup \
        --reset-all-parameters

Output::

    {
        "ParameterGroupName": "myclusterparametergroup",
        "ParameterGroupStatus": "Your parameter group has been updated but changes won't get applied until you reboot the associated Clusters."
    }

For more information, see `Amazon Redshift parameter groups <https://docs.aws.amazon.com/redshift/latest/mgmt/working-with-parameter-groups.html>`__ in the *Amazon Redshift Management Guide*.
