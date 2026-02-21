**To list security configurations in the current region**
 
Command::
 
    aws emr list-security-configurations

Output::

    {
        "SecurityConfigurations": [
            {
                "CreationDateTime": "2016-09-14T21:48:17.417+00:00",
                "Name": "MySecurityConfig-1"
            },
            {
                "CreationDateTime": "2016-09-14T21:48:17.417+00:00",
                "Name": "MySecurityConfig-2"
            }
        ]
    }
    