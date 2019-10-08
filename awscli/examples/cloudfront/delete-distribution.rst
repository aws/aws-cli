**To delete a CloudFront distribution**

The following command deletes a CloudFront distribution with the ID ``S11A16G5KZMEQD``::

  aws cloudfront delete-distribution --id S11A16G5KZMEQD --if-match 8UBQECEJX24ST

The distribution ID is available in the output of ``create-distribution`` and ``list-distributions``. The distribution must be disabled with ``update-distribution`` prior to deletion. The ETag value ``8UBQECEJX24ST`` for the ``if-match`` parameter is available in the output of ``update-distribution``, ``get-distribution`` or ``get-distribution-config``.
