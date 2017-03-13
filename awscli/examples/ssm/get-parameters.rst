**To list the values for a parameter**

This example lists the values for a parameter.

Command::

  aws ssm get-parameters --names "helloWorld"
  
Output::

  {
	"InvalidParameters": [],
	"Parameters": [
		{
			"Type": "String",
			"Name": "helloWorld",
			"Value": "good day sunshine"
		}
	]
  }
