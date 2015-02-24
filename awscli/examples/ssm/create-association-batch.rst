**To create multiple associations**

This example associates the configuration document ``My_Config_1`` with instance ``i-aabb2233``, and associates the configuration document ``My_Config_2`` with instance ``i-cdcd2233``. The output returns a list of successful and unsuccessful operations, if applicable.

Command::

  aws ssm create-association-batch --entries Name=My_Config_1,InstanceId=i-aabb2233 Name=My_Config_2,InstanceId=1-cdcd2233

Output::


 {
    "Successful": [
        {
            "InstanceId": "i-aabb2233", 
            "Date": 1424421071.939, 
            "Name": My_Config_1", 
            "Status": {
                "Date": 1424421071.939, 
                "Message": "Associated with My_Config_1", 
                "Name": "Associated"
            }
        }
    ], 
    "Failed": [
        {
            "Entry": {
                "InstanceId": "i-cdcd2233", 
                "Name": "My_Config_2"
            }, 
            "Message": "Association Already Exists", 
            "Fault": "Client"
        }
    ]
 }