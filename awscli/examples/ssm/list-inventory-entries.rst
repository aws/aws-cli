**To view custom inventory entries for an instance**

This example lists all the custom inventory entries for an instance.

Command::

  aws ssm list-inventory-entries --instance-id "i-0cb2b964d3e14fd9f" --type-name "Custom:RackInfo"

Output::

  {
	"InstanceId": "i-0cb2b964d3e14fd9f",
	"TypeName": "Custom:RackInfo",
	"Entries": [
		{
			"RackLocation": "Bay B/Row C/Rack D/Shelf E"
		}
	],
	"SchemaVersion": "1.0",
	"CaptureTime": "2016-08-22T10:01:01Z"
  }
