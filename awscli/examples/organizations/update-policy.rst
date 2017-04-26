**To rename a policy and give it a new description**

The following example shows how to rename a policy and give it a new description. The output confirms the new name and description text. 

Command::

  aws organizations update-policy --policy-id p-examplepolicyid111 --name Renamed-Policy --description "This description replaces the original."
  
The output confirms the new name and description text.

Output::

  {
    "Policy": {
      "Content": "{ \"Version\": \"2012-10-17\", \"Statement\": { \"Effect\": \"Allow\", \"Action\": \"ec2:*\", \"Resource\": \"*\" } }",
      "PolicySummary": {
        "Id": "p-examplepolicyid111",
        "AwsManaged": false,
        "Arn":"arn:aws:organizations::111111111111:policy/o-exampleorgid/service_control_policy/p-examplepolicyid111",
        "Description": "This description replaces the original.",
        "Name": "Renamed-Policy",
        "Type": "SERVICE_CONTROL_POLICY"
      }
    }
  }
  
**To change the JSON text associated with an SCP**

The following example shows how to replace the JSON text of the SCP in the preceding example with a new JSON policy text string that allows S3 actions instead of EC2 actions. 

Command::

  aws organizations update-policy --policy-id p-examplepolicyid111 --content file://policy-content.json
  
The file ``policy-content.json`` is a JSON document in the current folder that contains the following text::
  
  { 
    "Version": "2012-10-17",
    "Statement": { 
      "Effect": "Allow",
      "Action": "s3:*",
      "Resource": "*" 
    } 
  }

The output confirms the updated JSON text.

Output::

  {
    "Policy": {
      "Content": "{ \"Version\": \"2012-10-17\", \"Statement\": { \"Effect\": \"Allow\", \"Action\": \"s3:*\", \"Resource\": \"*\" } }",
      "PolicySummary": {    
        "Arn": "arn:aws:organizations::111111111111:policy/o-exampleorgid/service_control_policy/p-examplepolicyid111",
        "AwsManaged": false;
        "Description": "This description replaces the original.",
        "Id": "p-examplepolicyid111",
        "Name": "Renamed-Policy",
        "Type": "SERVICE_CONTROL_POLICY"
      }
    }