**To describe a cluster**

This example command provides a description of the specified cluster in your default region.

Command::

  aws ecs describe-clusters --cluster default

Output::

	{
	    "clusters": [
	        {
	            "clusterName": "default",
	            "status": "ACTIVE",
	            "clusterArn": "arn:aws:ecs:us-east-1:<aws_account_id>:cluster/default"
	        }
	    ],
	    "failures": []
	}
