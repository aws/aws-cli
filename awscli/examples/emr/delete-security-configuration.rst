**To delete a security configuration in the current region**

The following ``delete-security-configuration`` example deletes the security configuration named ``MySecurityConfig`` in the current region. This command produces no output. ::

    aws emr delete-security-configuration \
        --name MySecurityConfig
