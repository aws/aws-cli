**To import installation media**

The following ``import-installation-media`` imports installation media. ::

    aws rds import-installation-media \
        --custom-availability-zone-id rds-caz-EXAMPLE \
        --engine sqlserver-ee --engine-version 13.00.5292.0.v1 \
        --engine-installation-media-path SQLServerISO/en_sql_server_2016_enterprise_x64_dvd_8701793.iso \
        --os-installation-media-path WindowsISO/en_windows_server_2016_x64_dvd_9327751.iso

Output::
    
    {
        "InstallationMediaId": "b1zcEXAMPLE",
        "CustomAvailabilityZoneId": "rds-caz-EXAMPLE",
        "Engine": "sqlserver-ee",
        "EngineVersion": "13.00.5292.0.v1",
        "EngineInstallationMediaPath": "SQLServerISO/en_sql_server_2016_enterprise_x64_dvd_8701793.iso",
        "OSInstallationMediaPath": "WindowsISO/en_windows_server_2016_x64_dvd_9327751.iso",
        "Status": "Importing",
        "FailureCause": {}
    }

For more information, see `What is Amazon RDS on VMware? <https://docs.aws.amazon.com/AmazonRDS/latest/RDSonVMwareUserGuide/rds-on-vmware.html>`__ in the *Amazon RDS on VMware User Guide*.