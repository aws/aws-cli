**To display a patch baseline**

This example displays the details for a patch baseline.

Command::

  aws ssm get-patch-baseline --baseline-id "pb-00dbb759999aa2bc3"

Output::

  {
	"BaselineId":"pb-00dbb759999aa2bc3",
	"Name":"Windows-Server-2012R2",
	"PatchGroups":[
		"Web Servers"
	],
	"RejectedPatches":[
	
	],
	"GlobalFilters":{
		"PatchFilters":[
	
		]
	},
	"ApprovalRules":{
		"PatchRules":[
			{
				"PatchFilterGroup":{
				"PatchFilters":[
					{
						"Values":[
							"Important",
							"Critical"
						],
						"Key":"MSRC_SEVERITY"
					},
					{
						"Values":[
							"SecurityUpdates"
						],
						"Key":"CLASSIFICATION"
					},
					{
						"Values":[
							"WindowsServer2012R2"
						],
						"Key":"PRODUCT"
					}
				]
				},
				"ApproveAfterDays":5
			}
		]
	},
	"ModifiedDate":1480997823.81,
	"CreatedDate":1480997823.81,
	"ApprovedPatches":[
	
	],
	"Description":"Windows Server 2012 R2, Important and Critical security updates"
  }
