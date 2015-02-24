**To update the association status**

This example updates the association status of the association between instance ``i-1a2b3c4d`` and configuration document ``My_Config_1``.

Command::

  aws ssm update-association-status --name My_Config_1 --instance-id i-1a2b3c4d --association-status Date=1424421071.939,Name=Pending,Message=temp_status_change,AdditionalInfo=Additional-Config-Needed


Output::

 {
    "AssociationDescription": {
        "InstanceId": "i-1a2b3c4d", 
        "Date": 1424421071.939, 
        "Name": "My_Config_1", 
        "Status": {
            "Date": 1424421071.0, 
            "AdditionalInfo": "Additional-Config-Needed", 
            "Message": "temp_status_change", 
            "Name": "Pending"
        }
    }
 }