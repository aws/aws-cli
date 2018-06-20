**To list geographic locations that are supported for geolocation records**

The following ``list-geo-locations`` command returns a ``GeoLocationDetailsList`` element that lists the continents that are supported for geolocation records beginning with ``OC`` (Oceanea). The list is in alphabetical order and omits continents that precede Oceanea in alphabetical order::

  aws route53 list-geo-locations --start-continent-code OC

The following ``list-geo-locations`` command returns a ``GeoLocationDetailsList`` element that lists the countries that are supported for geolocation records beginning with ``LI`` (Liechtenstein). The list is in alphabetical order and omits countries that precede Liechtenstein in alphabetical order::

  aws route53 list-geo-locations --start-country-code LI

The following ``list-geo-locations`` command returns a ``GeoLocationDetailsList`` element that lists states in the United States that are supported for geolocation records beginning with ``IA``::

  aws route53 list-geo-locations --start-country-code US --start-subdivision-code IA
