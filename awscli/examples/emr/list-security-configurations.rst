**To list security configurations in the current region**
 
The following ``list-security-configurations`` example lists the security configurations in the current region. ::
 
    aws emr list-security-configurations

Output::

    {
        "SecurityConfigurations": [
            {
                "CreationDateTime": "2025-10-28T10:15:36.207000-04:00",
                "Name": "MySecurityConfig-1"
            },
            {
                "CreationDateTime": "2025-10-28T10:15:36.207000-04:00",
                "Name": "MySecurityConfig-2"
            }
        ]
    }
    
