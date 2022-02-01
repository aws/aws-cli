**To describe the installation media**

The following ``describe-installation-media`` example describes the installation media in the AWS Region. ::

    aws rds describe-installation-media

Output::

    {
        "InstallationMedia": [
            {
                "InstallationMediaId": "ahIOEXAMPLE",
                "CustomAvailabilityZoneId": "rds-caz-EXAMPLE1",
                "Engine": "sqlserver-ee",
                "EngineVersion": "13.00.5292.0.v1",
                "EngineInstallationMediaPath": "SQLServerISO/en_sql_server_2016_enterprise_x64_dvd_8701793.iso",
                "OSInstallationMediaPath": "WindowsISO/en_windows_server_2016_x64_dvd_9327751.iso",
                "Status": "Available",
                "FailureCause": {}
            },
            {
                "InstallationMediaId": "AzHmpfEXample",
                "CustomAvailabilityZoneId": "rds-caz-EXAMPLE2",
                "Engine": "sqlserver-ee",
                "EngineVersion": "13.00.5292.0.v1",
                "EngineInstallationMediaPath": "SQLServerISO/en_sql_server_2016_enterprise_x64_dvd_8701793.iso",
                "OSInstallationMediaPath": "WindowsISO/en_windows_server_2016_x64_dvd_9327751.iso",
                "Status": "Importing",
                "FailureCause": {}
            }
        ]
    }

For more information, see `What is Amazon RDS on VMware? <https://docs.aws.amazon.com/AmazonRDS/latest/RDSonVMwareUserGuide/rds-on-vmware.html>`__ in the *Amazon RDS on VMware User Guide*.