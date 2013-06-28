**To update the trust policy for an IAM role**

The following ``update-assume-role-policy`` commmand updates the trust policy for the role named ``Test-Role``::

  aws iam update-assume-role-policy --role-name Test-Tole --policy-document file://Test-Role-Trust-Policy.json

Output::

  {
      "ResponseMetadata": {
          "RequestId": "b9cd3e32-4a54-11e2-8110-65075b2814da"
      }
  }    
 
The trust policy is defined as a JSON document in the *Test-Role-Trust-Policy.json* file. (The file name and extension do not have significance.) The trust policy must specify a principal.

To update the permissions policy for a role, use the ``put-role-policy`` command.

For more information, see `Creating a Role`_ in the *Using IAM* guide.

.. _Creating a Role: http://docs.aws.amazon.com/IAM/latest/UserGuide/creating-role.html


