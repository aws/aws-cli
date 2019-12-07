**To describe the parameters in a DB cluster parameter group**

The following ``describe-db-cluster-parameters`` example retrieves details about the parameters in a DB cluster parameter group. ::

    aws rds describe-db-cluster-parameters \
        --db-cluster-parameter-group-name mydbclusterpg

Output::

    {
        "Parameters": [
            {
                "ParameterName": "allow-suspicious-udfs",
                "Description": "Controls whether user-defined functions that have only an xxx symbol for the main function can be loaded",
                "Source": "engine-default",
                "ApplyType": "static",
                "DataType": "boolean",
                "AllowedValues": "0,1",
                "IsModifiable": false,
                "ApplyMethod": "pending-reboot",
                "SupportedEngineModes": [
                    "provisioned"
                ]
            },
            {
                "ParameterName": "aurora_lab_mode",
                "ParameterValue": "0",
                "Description": "Enables new features in the Aurora engine.",
                "Source": "engine-default",
                "ApplyType": "static",
                "DataType": "boolean",
                "AllowedValues": "0,1",
                "IsModifiable": true,
                "ApplyMethod": "pending-reboot",
                "SupportedEngineModes": [
                    "provisioned"
                ]
            },
            ...some output truncated...
        ]
    }

For more information, see `Working with DB Parameter Groups and DB Cluster Parameter Groups <https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/USER_WorkingWithParamGroups.html>`__ in the *Amazon Aurora User Guide*.
