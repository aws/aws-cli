**To delete installation media**

The following ``delete-installation-media`` example deletes installation media. ::

    aws rds delete-installation-media \
        --installation-media-id NcNrEXAMPLE

Output::

    {
        "InstallationMediaId": "NcNrEXAMPLE",
        "CustomAvailabilityZoneId": "rds-caz-EXAMPLE",
        "Engine": "sqlserver-ee",
        "EngineVersion": "13.00.5292.0.v1",
        "EngineInstallationMediaPath": "SQLServerISO/en_sql_server_2016_enterprise_x64_dvd_8701793.iso",
        "OSInstallationMediaPath": "WindowsISO/en_windows_server_2016_x64_dvd_9327751.iso",
        "Status": "Deleting",
        "FailureCause": {}
    }

For more information, see `What is Amazon RDS on VMware? <https://docs.aws.amazon.com/AmazonRDS/latest/RDSonVMwareUserGuide/rds-on-vmware.html>`__ in the *Amazon RDS on VMware User Guide*.