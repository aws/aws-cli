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

To list the name and value of multiple parameters the --query argument can be used with a list of names.

Command::
  
  aws ssm get-parameters --names key1 key2 --query "Parameters[*].{Name:Name,Value:Value}"

Output::
  
  [
    {
        "Name": "key1",
        "Value": "value1"
    },
    {
        "Name": "key2",
        "Value": "value2"
    }
  ]

