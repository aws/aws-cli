**To start maintenance**

The following ``start-maintenance`` example manually starts maintenance on the specified Chef Automate server in your default region. This command can be useful if an earlier, automated maintenance attempt failed, and the underlying cause of maintenance failure has been resolved. ::

    aws opsworks-cm start-maintenance --server-name 'automate-06'

The output shows you information similar to the following about the maintenance request. ::

    {
        "Server": { 
            "BackupRetentionCount": 8,
            "CreatedAt": 2016-07-29T13:38:47.520Z,
            "DisableAutomatedBackup": TRUE,
            "Endpoint": "https://opsworks-cm.us-east-1.amazonaws.com",
            "Engine": "Chef",
            "EngineAttributes": [ 
                { 
                    "Name": "CHEF_DELIVERY_ADMIN_PASSWORD",
                    "Value": "1Password1"
                }
            ],
            "EngineModel": "Single",
            "EngineVersion": "12",
            "InstanceProfileArn": "arn:aws:iam::1019881987024:instance-profile/automate-06-1010V4UU2WRM2",
            "InstanceType": "m4.large",
            "KeyPair": "",
            "MaintenanceStatus": "SUCCESS",
            "PreferredBackupWindow": "",
            "PreferredMaintenanceWindow": "",
            "SecurityGroupIds": [ "sg-1a24c270" ],
            "ServerArn": "arn:aws:iam::1019881987024:instance/automate-06-1010V4UU2WRM2",
            "ServerName": "automate-06",
            "ServiceRoleArn": "arn:aws:iam::1019881987024:role/aws-opsworks-cm-service-role.1114810729735",
            "Status": "HEALTHY",
            "StatusReason": "",
            "SubnetIds": [ "subnet-49436a18" ]
        }
    }

For more information, see `StartMaintenance <http://docs.aws.amazon.com/opsworks-cm/latest/APIReference/API_StartMaintenance.html>`_ in the *AWS OpsWorks for Chef Automate API Reference*.
