**To delete an HSM configuration**

The following ``delete-hsm-configuration`` example deletes the specified HSM configuration from the current AWS account. ::

    aws redshift delete-hsm-configuration \
        --hsm-configuration-identifier myhsmconnection

This command produces no output.

For more information, see `Amazon Redshift database encryption <https://docs.aws.amazon.com/redshift/latest/mgmt/working-with-db-encryption.html>`__ in the *Amazon Redshift Management Guide*.
