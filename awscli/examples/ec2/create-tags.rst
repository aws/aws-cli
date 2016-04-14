**To add a tag to a resource**

This example adds the tag ``Stack=production`` to the specified image, or overwrites an existing tag for the AMI where the tag key is ``Stack``. If the command succeeds, no output is returned.

Command::

  aws ec2 create-tags --resources ami-78a54011 --tags Key=Stack,Value=production

**To add tags to multiple resources**

This example adds (or overwrites) two tags for an AMI and an instance. One of the tags contains just a key (``webserver``), with no value (we set the value to an empty string). The other tag consists of a key (``stack``) and value (``Production``). If the command succeeds, no output is returned.

Command::

  aws ec2 create-tags --resources ami-1a2b3c4d i-1234567890abcdef0 --tags Key=webserver,Value=   Key=stack,Value=Production

**To add tags with special characters**

This example adds the tag ``[Group]=test`` for an instance. The square brackets ([ and ]) are special characters, and must be escaped. If you are using Windows, surround the value with (\"):

Command::

  aws ec2 create-tags --resources i-1234567890abcdef0 --tags Key=\"[Group]\",Value=test

If you are using Windows PowerShell, break out the characters with a backslash (\\), surround them with double quotes ("), and then surround the entire key and value structure with single quotes ('):

Command::

  aws ec2 create-tags --resources i-1234567890abcdef0 --tags 'Key=\"[Group]\",Value=test'

If you are using Linux or OS X, enclose the entire key and value structure with single quotes ('), and then enclose the element with the special character with double quotes ("):

Command::

  aws ec2 create-tags --resources i-1234567890abcdef0 --tags 'Key="[Group]",Value=test'

