The following command creates a replication task to copy data from one DB instance behind a DMS endpoint to another using a replication instance::

  aws dms create-replication-task --replicationtask-identifier my-replication-task --target-endpoint-arn arn:aws:dms:us-east-1:123456789012:endpoint:HTWNT57CLN2WGVBUJQXJZASXWE --source-endpoint-arn arn:aws:dms:us-east-1:123456789012:endpoint:ZW5UAN6P4E77EC7YWHK4RZZ3BE --replication-instance-arn arn:aws:dms:us-east-1:123456789012:rep:6UTDJGBOUS3VI3SUWA66XFJCJQ --migration-type full-load --table-mappings 'file://table-mappings.json'

The file ``table-mappings.json`` is a JSON document in the current folder that specifies table mappings::

  {
    "TableMappings": [
      {
        "Type": "Include",
        "SourceSchema": "company",
        "SourceTable": "emp%"
      },
      {
        "Type": "Include",
        "SourceSchema": "employees",
        "SourceTable": "%"
      },
      {
        "Type": "Exclude",
        "SourceSchema": "source101",
        "SourceTable": "dep%"
      },
      {
        "Type": "Exclude",
        "SourceSchema": "source102",
        "SourceTable": "%"
      },
      {
        "Type": "Explicit",
        "SourceSchema": "company",
        "SourceTable": "managers"
      },
      {
        "Type": "Explicit",
        "SourceSchema": "company",
        "SourceTable": "locations"
      }
      ]
  }


Output::

  {
    "ReplicationTask": {
      "SourceEndpointArn": "arn:aws:dms:us-east-1:123456789012:endpoint:ZW5UAN6P4E77EC7YWHK4RZZ3BE",
      "ReplicationTaskIdentifier": "task1",
      "ReplicationInstanceArn": "arn:aws:dms:us-east-1:123456789012:rep:6UTDJGBOUS3VI3SUWA66XFJCJQ",
      "TableMappings": "{\n \"TableMappings\": [\n {\n \"Type\":\"Include\",\n \"SourceSchema\": \"/\",\n \"SourceTable\": \"/\"\n}\n ]\n}\n\n",
      "Status": "creating",
      "ReplicationTaskArn": "arn:aws:dms:us-east-1:123456789012:task:OEAMB3NXSTZ6LFYZFEPPBBXPYM",
      "ReplicationTaskCreationDate": 1457658407.492,
      "MigrationType": "full-load",
      "TargetEndpointArn": "arn:aws:dms:us-east-1:123456789012:endpoint:ASXWXJZLNWNT5HTWCGV2BUJQ7E",
      "ReplicationTaskSettings": "{\"TargetMetadata\":{\"TargetSchema\":\"\",\"SupportLobs\":true,\"FullLobMode\":true,\"LobChunkSize\":64,\"LimitedSizeLobMode\":false,\"LobMaxSize\":0},\"FullLoadSettings\":{\"FullLoadEnabled\":true,\"ApplyChangesEnabled\":false,\"TargetTablePrepMode\":\"DROP_AND_CREATE\",\"CreatePkAfterFullLoad\":false,\"StopTaskCachedChangesApplied\":false,\"StopTaskCachedChangesNotApplied\":false,\"ResumeEnabled\":false,\"ResumeMinTableSize\":100000,\"ResumeOnlyClusteredPKTables\":true,\"MaxFullLoadSubTasks\":8,\"TransactionConsistencyTimeout\":600,\"CommitRate\":10000},\"Logging\":{\"EnableLogging\":false}}"
    }
  }
