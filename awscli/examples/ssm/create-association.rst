**To associate a configuration document**

This example associates configuration document ``My_Config_File`` with instance ``i-1a2b3c4d``.

Command::

  aws ssm create-association --instance-id i-1a2b3c4d --name "My_Config_File"

Output::

   {
     "AssociationDescription": {
         "InstanceId": "i-1a2b3c4d", 
         "Date": 1424354424.842, 
         "Name": "My_Config_File", 
         "Status": {
             "Date": 1424354424.842, 
             "Message": "Associated with My_Config_File", 
             "Name": "Associated"
            }
        }
    }

