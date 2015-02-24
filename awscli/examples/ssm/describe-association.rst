**To describe an association**

This example describes the association between instance ``i-1a2b3c4d`` and ``My_Config_File``.

Command::

  aws ssm describe-association --instance-id i-1a2b3c4d --name "My_Config_File"

Output::

 {
    "AssociationDescription": {
        "InstanceId": "i-1a2b3c4d", 
        "Date": 1424419009.036, 
        "Name": "My_Config_File", 
        "Status": {
            "Date": 1424419196.804, 
            "AdditionalInfo": "{agent=EC2Config,ver=3.0.54,osver=6.3.9600,os=Windows Server 2012 R2 Standard,lang=en-US}", 
            "Message": "RunId=0198dadc-aaaa-4150-875f-exampleba3d, status:InProgress, code:0, message:RuntimeStatusCounts=[PassedAndReboot=1], RuntimeStatus=[aws:domainJoin={PassedAndReboot,Domain join Succeeded to domain: test.ssm.com}]", 
            "Name": "Pending"
         }
     }
 }