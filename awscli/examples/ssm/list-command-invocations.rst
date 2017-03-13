**To list the invocations of a specific command**

This example lists all the invocations of a command.

Command::

  aws ssm list-command-invocations --command-id "b8eac879-0541-439d-94ec-47a80d554f44" --details

Output::

  {
	"CommandInvocations": [
		{
			"Comment": "IP config",
			"Status": "Success",
			"CommandPlugins": [
				{
					"Status": "Success",
					"ResponseStartDateTime": 1487794396.651,
					"StandardErrorUrl": "",
					"OutputS3BucketName": "",
					"OutputS3Region": "us-west-2",
					"OutputS3KeyPrefix": "",
					"ResponseCode": 0,
					"Output": "eth0      Link encap:Ethernet  HWaddr 06:41:38:F5:D6:EF  \n          inet addr:172.31.44.222  Bcast:172.31.47.255  Mask:255.255.240.0\n          inet6 addr: fe80::441:38ff:fef5:d6ef/64 Scope:Link\n          UP BROADCAST RUNNING MULTICAST  MTU:9001  Metric:1\n          RX packets:186705 errors:0 dropped:0 overruns:0 frame:0\n          TX packets:188811 errors:0 dropped:0 overruns:0 carrier:0\n          collisions:0 txqueuelen:1000 \n          RX bytes:91749280 (87.4 MiB)  TX bytes:31721645 (30.2 MiB)\n\nlo        Link encap:Local Loopback  \n          inet addr:127.0.0.1  Mask:255.0.0.0\n         inet6 addr: ::1/128 Scope:Host\n          UP LOOPBACK RUNNING  MTU:65536  Metric:1\n          RX packets:2 errors:0 dropped:0 overruns:0 frame:0\n          X packets:2 errors:0 dropped:0 overruns:0 carrier:0\n          collisions:0 txqueuelen:1 \n          RX bytes:140 (140.0 b)  TX bytes:140 (140.0 b)\n\n",
					"ResponseFinishDateTime": 1487794396.655,
					"StatusDetails": "Success",
					"StandardOutputUrl": "",
					"Name": "aws:runShellScript"
				}
			],
			"ServiceRole": "",
			"InstanceId": "i-0cb2b964d3e14fd9f",
			"DocumentName": "AWS-RunShellScript",
			"NotificationConfig": {
				"NotificationArn": "",
				"NotificationEvents": [],
				"NotificationType": ""
			},
			"StatusDetails": "Success",
			"StandardOutputUrl": "",
			"StandardErrorUrl": "",
			"InstanceName": "",
			"CommandId": "b8eac879-0541-439d-94ec-47a80d554f44",
			"RequestedDateTime": 1487794396.363
		}
	]
  }
