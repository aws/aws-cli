**To update the comment for a specified hosted zone**

The following ``update-hosted-zone-comment`` command updates the current comment for the hosted zone to the value that is specified in the ``comment`` parameter::

  aws route53 update-hosted-zone-comment --id Z36KTIQEXAMPLE --comment "Hosted zone for internal testing for the company website"

The maximum length of the comment is 256 bytes.