**To describe your WorkSpace directories**

This example describes all of your WorkSpace directories.

Command::

  aws workspaces describe-workspace-directories

Output::

  {
    "Directories" : [
      {
        "CustomerUserName" : "Administrator",
        "DirectoryId" : "d-906735683d",
        "DirectoryName" : "example.awsapps.com",
        "SubnetIds" : [
          "subnet-af0e2a87",
          "subnet-657e7a23"
        ],
        "WorkspaceCreationProperties" :
        {
          "EnableInternetAccess" : false,
          "EnableWorkDocs" : false,
          "UserEnabledAsLocalAdministrator" : true
        },
        "Alias" : "example",
        "State" : "REGISTERED",
        "DirectoryType" : "SIMPLE_AD",
        "RegistrationCode" : "SLiad+S393HD",
        "IamRoleId" : "arn:aws:iam::972506530580:role/workspaces_DefaultRole",
        "DnsIpAddresses" : [
          "10.0.2.190",
          "10.0.1.202"
        ],
        "WorkspaceSecurityGroupId" : "sg-6e40640b"
      },
      {
        "CustomerUserName" : "Administrator",
        "DirectoryId" : "d-906732325d",
        "DirectoryName" : "exampledomain.com",
        "SubnetIds" : [
          "subnet-775a6531",
          "subnet-435c036b"
        ],
        "WorkspaceCreationProperties" :
        {
          "EnableInternetAccess" : false,
          "EnableWorkDocs" : true,
          "UserEnabledAsLocalAdministrator" : true
        },
        "Alias" : "example-domain",
        "State" : "REGISTERED",
        "DirectoryType" : "AD_CONNECTOR",
        "RegistrationCode" : "SLiad+UBZGNH",
        "IamRoleId" : "arn:aws:iam::972506530580:role/workspaces_DefaultRole",
        "DnsIpAddresses" : [
          "50.0.2.223",
          "50.0.2.184"
        ]
      }
    ]
  }
