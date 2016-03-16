The following command creates a source endpoint for a MySQL RDS DB instance named ``mydb.cx1llnox7iyx.uswest-2.rds.amazonaws.com``::

  aws dms create-endpoint --endpoint-identifier test-endpoint-1 --endpoint-type source --engine-name mysql --username username --password password --server-name mydb.cx1llnox7iyx.uswest-2.rds.amazonaws.com --port 3306

Output::

  {
    "Endpoint": {
      "Username": "username",
      "Status": "active",
      "EndpointArn": "arn:aws:dms:us-east-1:123456789012:endpoint:RAAR3R22XSH46S3PWLC3NJAWKM",
      "ServerName": "mydb.cx1llnox7iyx.us-west-2.rds.amazonaws.com",
      "EndpointType": "SOURCE",
      "KmsKeyId": "arn:aws:kms:us-east-1:123456789012:key/4c1731d6-5435-ed4d-be13-d53411a7cfbd",
      "EngineName": "mysql",
      "EndpointIdentifier": "test-endpoint-1",
      "Port": 3306
    }
  }
