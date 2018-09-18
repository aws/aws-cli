**To set subscription attributes**

This example sets the RawMessageDelivery attribute to an SQS subscription.

Command::

  aws sns set-subscription-attributes --subscription-arn arn:aws:sns:us-east-1:012345678912:mytopic:f248de18-2cf6-578c-8592-b6f1eaa877dc --attribute-name RawMessageDelivery --attribute-value true
  
Output::

  None.

This example sets a FilterPolicy attribute to an SQS subscription.

Command::

  aws sns set-subscription-attributes --subscription-arn arn:aws:sns:us-east-1:012345678912:mytopic:f248de18-2cf6-578c-8592-b6f1eaa877dc --attribute-name FilterPolicy --attribute-value "{ \"anyMandatoryKey\": [\"any\", \"of\", \"these\"] }"

Output::

  None.

This example removes the FilterPolicy attribute from an SQS subscription.

Command::

  aws sns set-subscription-attributes --subscription-arn arn:aws:sns:us-east-1:012345678912:mytopic:f248de18-2cf6-578c-8592-b6f1eaa877dc --attribute-name FilterPolicy --attribute-value "{}"

Output::

  None.
