**To delete tags for a domain**

The following ``delete-tags-for-domain`` command deletes three tags::

  aws route53domains delete-tags-for-domain --region us-east-1 --domain-name example.com --tags-to-delete tag1 tag2 tag3

If the default region is us-east-1, you can omit the ``region`` parameter.