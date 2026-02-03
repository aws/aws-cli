**To list available EMR Studios**
 
The following ``list-studios`` example lists the EMR Studios in the AWS account::
 
    aws emr list-studios

Output::

    {
        "Studios": [
            {
                "StudioId": "es-XXXXXXX132E0X7R0W7GAS1MVB",
                "Name": "My_EMR_Studio",
                "Url": "https://es-XXXXXXX132E0X7R0W7GAS1MVB.emrstudio-prod.us-east-1.amazonaws.com",
                "AuthMode": "IAM",
                "CreationTime": "2025-10-28T11:09:33.624000-04:00"
            }
        ]
    }


For more information, see `Monitor, delete and updatMonitor, update and delete Amazon EMR Studio resources <https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-studio-manage-studio.html>`__ in the *Amazon EMR Management Guide*.
    
