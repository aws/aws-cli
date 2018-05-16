**To determine whether a geographic location is supported for geolocation records**

The following ``get-geo-location`` command returns a ``GeoLocationDetails`` element that indicates that the continent code ``AF`` is associated with Africa::

  aws route53 get-geo-location --continent-code AF

The following ``get-geo-location`` command returns a ``GeoLocationDetails`` element that indicates that the country code ``LI`` is associated with Liechtenstein::

  aws route53 get-geo-location --continent-code AF

The following ``get-geo-location`` command returns a ``GeoLocationDetails`` element that indicates that the country code ``US`` and subdivision code ``WA`` are associated with the United States state Washington::

  aws route53 get-geo-location --country-code US --subdivision-code WA
