**To add a tag to a resource**

This example adds the tag ``Stack=production`` to the specified image, or overwrites an existing tag for the AMI where
the tag key is ``Stack``.

Command::

  aws ec2 create-tags --resources ami-78a54011 --tags Key=Stack,Value=production

Output::

  {
      "return": "true"
  }

**To add tags to multiple resources**

This example adds (or overwrites) two tags for an AMI and an instance. One of the tags contains just a key
(``webserver``), with no value (we set the value to an empty string). The other tag consists of a key (``stack``) and
value (``Production``).

Command::

  aws ec2 create-tags --resources ami-1a2b3c4d i-10a64379 --tags Key=webserver,Value=   Key=stack,Value=Production

**To add tags with special characters**

If you have any special characters in your tags that must be escaped, such as square bracket ([ and ]) characters,
surround the entire tag with quotes.

* On Linux, OS X, or in Windows Powershell, use single quotes to surround the tag::

  aws ec2 create-tags --resources i-1a2b3c4d --tags Key='[Group]',Value=test

* On the basic (non-Powershell) Windows command-prompt, use double quotes instead::

  aws ec2 create-tags --resources i-1a2b3c4d --tags Key="[Group]",Value=test

