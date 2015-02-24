**To list your associations for a specific instance**

This example lists all the associations for instance ``i-1a2b3c4d``.

Command::

  aws ssm list-associations --association-filter-list key=InstanceId,value=i-1a2b3c4d

Output::

 {
    "Associations": [
        {
            "InstanceId": "i-1a2b3c4d", 
            "Name": "My_Config_File"
        }
    ]
 }

**To list your associations for a specific configuration document**

This example lists all associations for the configuration document ``My_Config_File``.

Command::

  aws ssm list-associations --association-filter-list key=Name,value=My_Config_File

Output::

 {
    "Associations": [
        {
            "InstanceId": "i-1a2b3c4d", 
            "Name": "My_Config_File"
        }, 
        {
            "InstanceId": "i-rraa3344", 
            "Name": "My_Config_File"
        }
    ]
 }

