**To get the limit on records for a hosted zone or Amazon VPCs for a private hosted zone**

**Records that you can create in a specified hosted zone**

The following ``get-hosted-zone-limit`` command gets the current limit on the number of records that you can create in the hosted zone with a ``hosted-zone-id`` of ``Z1OX3WQEXAMPLE``::

  aws route53 get-hosted-zone-limit --type MAX_RRSETS_BY_ZONE --hosted-zone-id Z1OX3WQEXAMPLE

**Amazon VPCs that you can associate with a specified private hosted zone**

The following ``get-hosted-zone-limit`` command gets the current limit on the number of Amazon VPCs that you can associate with a private hosted zone with a ``hosted-zone-id`` of ``Z2PY4XREXAMPLE``::

  aws route53 get-hosted-zone-limit --type MAX_VPCS_ASSOCIATED_BY_ZONE --hosted-zone-id Z2PY4XREXAMPLE
