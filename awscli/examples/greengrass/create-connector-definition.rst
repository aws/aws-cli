**To create a Greengrass connector**

The following ``create-connector-definition`` example creates a Greengrass connector to publish messages to an Amazon SNS topic.  The topic must already exist and you must have a policy added to the Greengrass group role that allows the ``sns:Publish`` action on the target SNS topic. ::

    aws greengrass create-connector-definition \
        --name MySNSConnector \
        --initial-version "{\"Connectors\": [{\"Id\":\"MySNSConnector\",\"ConnectorArn\":\"arn:aws:greengrass:us-west-2::/connectors/SNS/versions/1\",\"Parameters\": {\"DefaultSNSArn\":\"arn:aws:sns:us-west-2:123456789012:GGConnectorTopic\"}}]}"

Output::

   {
       "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/connectors/b5c4ebfd-f672-49a3-83cd-31c7216a7bb8",
       "CreationTimestamp": "2019-06-19T19:30:01.300Z",
       "Id": "b5c4ebfd-f672-49a3-83cd-31c7216a7bb8",
       "LastUpdatedTimestamp": "2019-06-19T19:30:01.300Z",
       "LatestVersion": "63c57963-c7c2-4a26-a7e2-7bf478ea2623",
       "LatestVersionArn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/connectors/b5c4ebfd-f672-49a3-83cd-31c7216a7bb8/versions/63c57963-c7c2-4a26-a7e2-7bf478ea2623",
       "Name": "MySNSConnector"
   }

For more information, see `SNS (AWS-Provided Greengrass Connectors) <https://docs.aws.amazon.com/greengrass/latest/developerguide/sns-connector.html>`__ in the **AWS IoT Greengrass Developer Guide**.
