**To get information about an OU**

The following example shows how to request details about an OU: ::

	aws organizations describe-organizational-unit --organizational-unit-id ou-examplerootid111-exampleouid111
	
The output includes an OrganizationUnit object that contains the details about the OU: ::

	{
		"OrganizationalUnit": {
			"Name": "Accounting Group",
			"Arn": "arn:aws:organizations::o-exampleorgid:ou/o-exampleorgid/ou-examplerootid111-exampleouid111",
			"Id": "ou-examplerootid111-exampleouid111"
		}
	}