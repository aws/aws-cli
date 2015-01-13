**To describe linked EC2-Classic instances**

This example lists all of your linked EC2-Classic instances.

Command::

  aws ec2 describe-classic-link-instances

Output::

	{
		"Instances": [
			{
				"InstanceId": "i-1a2b3c4d", 
				"VpcId": "vpc-88888888", 
				"Groups": [
					{
						"GroupId": "sg-11122233"
					}                   
				], 
				"Tags": [
					{
						"Value": "ClassicInstance", 
						"Key": "Name"
					}
				]
			}, 
			{
				"InstanceId": "i-ab12cd34", 
				"VpcId": "vpc-12312312", 
				"Groups": [
					{
						"GroupId": "sg-aabbccdd"
					}  
				], 
				"Tags": [
					{
						"Value": "ClassicInstance2", 
						"Key": "Name"
					}
				]
			}
		]
	}
	
This example lists all of your linked EC2-Classic instances, and filters the response to include only instances that are linked to VPC vpc-88888888.

Command::

  aws ec2 describe-classic-link-instances --filter "Name=vpc-id,Values=vpc-88888888"

Output::

	{
		"Instances": [
			{
				"InstanceId": "i-1a2b3c4d", 
				"VpcId": "vpc-88888888", 
				"Groups": [
					{
						"GroupId": "sg-11122233"
					}                   
				], 
				"Tags": [
					{
						"Value": "ClassicInstance", 
						"Key": "Name"
					}
				]
			}
		]
	}
