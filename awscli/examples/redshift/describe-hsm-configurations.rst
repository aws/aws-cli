**To describe HSM configurations**

The following ``describe-hsm-configurations`` example displays details for the available HSM configurations for the calling AWS account. ::

    aws redshift describe-hsm-configurations \
        --hsm-configuration-identifier myhsmconnection

Output::

    {
        "HsmConfigurations": [
            {
                "HsmConfigurationIdentifier": "myhsmconnection",
                "Description": "My HSM connection",
                "HsmIpAddress": "192.0.2.09",
                "HsmPartitionName": "myhsmpartition",
                "Tags": []
            }
        ]
    }

For more information, see `Encryption using hardware security modules <https://docs.aws.amazon.com/redshift/latest/mgmt/working-with-db-encryption.html#working-with-HSM>`__ in the *Amazon Redshift Management Guide*.
