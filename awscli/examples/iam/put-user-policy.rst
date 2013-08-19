**To attach a policy to an IAM user**

The following ``put-user-policy`` commmand attaches a policy to the IAM user named ``Bob``::

  aws iam put-user-policy --user-name Bob --policy-name ExamplePolicy --policy-document file://AdminPolicy.json

Output::

  {
      "ResponseMetadata": {
          "RequestId": "b9cd3e32-4a54-11e2-8110-65075b2814da"
      }
  }    

The policy is defined as a JSON document in the *AdminPolicy.json* file. (The file name and extension do not have significance.)

For more information, see `Adding a New User to Your AWS Account`_ in the *Using IAM* guide.

.. _Adding a New User to Your AWS Account: http://docs.aws.amazon.com/IAM/latest/UserGuide/Using_SettingUpUser.html





