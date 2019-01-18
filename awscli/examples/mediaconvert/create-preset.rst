**To create a custom output preset**

The following example creates a custom output preset based on the output settings that are specified in the file preset.json that resides
on your system. You can specify the category, description, and name either in the JSON file or at the command line:

Command::
     aws --endpoint-url=https://abcd1234.mediaconvert.region-name-1.amazonaws.com --region=region-name-1 mediaconvert create-preset --cli-input-json file://~/preset.json

If you create your preset JSON file by using get-preset and then modifying the file, make sure to remove the following key-value pairs: LastUpdated, Arn, Type, and CreatedAt.

To get your account-specific endpoint, use describe-endpoints, or send the command without the endpoint. The service will return an error and your endpoint.