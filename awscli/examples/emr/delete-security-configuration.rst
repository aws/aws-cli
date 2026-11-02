**To delete a security configuration in the current region**

The following ``delete-security-configuration`` example deletes the security configuration named ``MySecurityConfig`` in the current region. ::

    aws emr delete-security-configuration \
        --name MySecurityConfig

This command produces no output.

For more information, see `Use security configurations to set up Amazon EMR cluster security <https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-security-configurations.html>`__ in the *Amazon EMR Management Guide*.
