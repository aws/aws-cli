**To find the Amazon DocumentDB instance options you can order**

The following ``describe-orderable-db-instance-options`` example lists all instance options for Amazon DocumentDB for a region. ::

    aws docdb describe-orderable-db-instance-options \
        --engine docdb

Output::

    {
        "OrderableDBInstanceOptions": [
            {
                "Vpc": true,
                "AvailabilityZones": [
                    {
                        "Name": "us-west-2a"
                    },
                    {
                        "Name": "us-west-2b"
                    },
                    {
                        "Name": "us-west-2c"
                    },
                    {
                        "Name": "us-west-2d"
                    }
                ],
                "EngineVersion": "3.6.0",
                "DBInstanceClass": "db.r4.16xlarge",
                "LicenseModel": "na",
                "Engine": "docdb"
            },
            {
                "Vpc": true,
                "AvailabilityZones": [
                    {
                        "Name": "us-west-2a"
                    },
                    {
                        "Name": "us-west-2b"
                    },
                    {
                        "Name": "us-west-2c"
                    },
                    {
                        "Name": "us-west-2d"
                    }
                ],
                "EngineVersion": "3.6.0",
                "DBInstanceClass": "db.r4.2xlarge",
                "LicenseModel": "na",
                "Engine": "docdb"
            },
            {
                "Vpc": true,
                "AvailabilityZones": [
                    {
                        "Name": "us-west-2a"
                    },
                    {
                        "Name": "us-west-2b"
                    },
                    {
                        "Name": "us-west-2c"
                    },
                    {
                        "Name": "us-west-2d"
                    }
                ],
                "EngineVersion": "3.6.0",
                "DBInstanceClass": "db.r4.4xlarge",
                "LicenseModel": "na",
                "Engine": "docdb"
            },
            {
                "Vpc": true,
                "AvailabilityZones": [
                    {
                        "Name": "us-west-2a"
                    },
                    {
                        "Name": "us-west-2b"
                    },
                    {
                        "Name": "us-west-2c"
                    },
                    {
                        "Name": "us-west-2d"
                    }
                ],
                "EngineVersion": "3.6.0",
                "DBInstanceClass": "db.r4.8xlarge",
                "LicenseModel": "na",
                "Engine": "docdb"
            },
            {
                "Vpc": true,
                "AvailabilityZones": [
                    {
                        "Name": "us-west-2a"
                    },
                    {
                        "Name": "us-west-2b"
                    },
                    {
                        "Name": "us-west-2c"
                    },
                    {
                        "Name": "us-west-2d"
                    }
                ],
                "EngineVersion": "3.6.0",
                "DBInstanceClass": "db.r4.large",
                "LicenseModel": "na",
                "Engine": "docdb"
            },
            {
                "Vpc": true,
                "AvailabilityZones": [
                    {
                        "Name": "us-west-2a"
                    },
                    {
                        "Name": "us-west-2b"
                    },
                    {
                        "Name": "us-west-2c"
                    },
                    {
                        "Name": "us-west-2d"
                    }
                ],
                "EngineVersion": "3.6.0",
                "DBInstanceClass": "db.r4.xlarge",
                "LicenseModel": "na",
                "Engine": "docdb"
            }
        ]
    }


For more information, see `Adding an Amazon DocumentDB Instance to a Cluster <https://docs.aws.amazon.com/documentdb/latest/developerguide/db-instance-add.html>`__ in the *Amazon DocumentDB Developer Guide*.
