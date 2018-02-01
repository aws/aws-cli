**To create a new job**

You can create a job either by using a preset to define your output settings or by providing all your settings in a JSON job file.

*Example with all settings in a separate JSON file*

This example creates a transcoding job with the settings you specify in a JSON file residing on your system. 

You can use the AWS Elemental MediaConvert `console` to generate the JSON job specification by choosing your job settings and then choosing **Show job JSON** at the bottom of the **Job** section.
.. _`console`: https://console.aws.amazon.com/mediaconvert

To get your account-specific endpoint, send the command without the endpoint. The service will return an error and your endpoint.

Command::

  aws --endpoint-url=https://abcd1234.mediaconvert.region-name-1.amazonaws.com --region=region-name-1 mediaconvert create-job --cli-input-json=file://~/job.json

Output::

If your request is successful, AWS Elemental MediaConvert returns the JSON job specification you sent with your request.

*Example using a system preset*        
