# Copyright 2012-2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.

# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at

#     http://aws.amazon.com/apache2.0/

# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.


def format_text(data, stream):
    _format_text(data, stream)


def _format_text(item, stream, identifier=None, scalar_keys=None):
    if isinstance(item, dict):
        _format_dict(scalar_keys, item, identifier, stream)
    elif isinstance(item, list):
        _format_list(item, identifier, stream)
    else:
        # If it's not a list or a dict, we just write the scalar
        # value out directly.
        stream.write(str(item))
        stream.write('\n')


def _format_list(item, identifier, stream):
    if not item:
        return
    if any(isinstance(el, dict) for el in item):
        all_keys = _all_scalar_keys(item)
        for element in item:
            _format_text(element, stream=stream, identifier=identifier,
                         scalar_keys=all_keys)
    elif any(isinstance(el, list) for el in item):
        scalar_elements, non_scalars = _partition_list(item)
        if scalar_elements:
            _format_scalar_list(scalar_elements, identifier, stream)
        for non_scalar in non_scalars:
            _format_text(non_scalar, stream=stream,
                         identifier=identifier)
    else:
        _format_scalar_list(item, identifier, stream)


def _partition_list(item):
    scalars = []
    non_scalars = []
    for element in item:
        if isinstance(element, (list, dict)):
            non_scalars.append(element)
        else:
            scalars.append(element)
    return scalars, non_scalars


def _format_scalar_list(elements, identifier, stream):
    if identifier is not None:
        for item in elements:
            stream.write('%s\t%s\n' % (identifier.upper(),
                                       item))
    else:
        # For a bare list, just print the contents.
        stream.write('\t'.join([str(item) for item in elements]))
        stream.write('\n')


def _format_dict(scalar_keys, item, identifier, stream):
    scalars, non_scalars = _partition_dict(item, scalar_keys=scalar_keys)
    if scalars:
        if identifier is not None:
            scalars.insert(0, identifier.upper())
        stream.write('\t'.join(scalars))
        stream.write('\n')
    for new_identifier, non_scalar in non_scalars:
        _format_text(item=non_scalar, stream=stream,
                     identifier=new_identifier)


def _all_scalar_keys(list_of_dicts):
    keys_seen = set()
    for item_dict in list_of_dicts:
        for key, value in item_dict.items():
            if not isinstance(value, (dict, list)):
                keys_seen.add(key)
    return list(sorted(keys_seen))


def _partition_dict(item_dict, scalar_keys):
    # Given a dictionary, partition it into two list based on the
    # values associated with the keys.
    # {'foo': 'scalar', 'bar': 'scalar', 'baz': ['not, 'scalar']}
    # scalar = [('foo', 'scalar'), ('bar', 'scalar')]
    # non_scalar = [('baz', ['not', 'scalar'])]
    scalar = []
    non_scalar = []
    if scalar_keys is None:
        # scalar_keys can have more than just the keys in the item_dict,
        # but if user does not provide scalar_keys, we'll grab the keys
        # from the current item_dict
        for key, value in sorted(item_dict.items()):
            if isinstance(value, (dict, list)):
                non_scalar.append((key, value))
            else:
                scalar.append(str(value))
    else:
        for key in scalar_keys:
            scalar.append(str(item_dict.get(key, '')))
        remaining_keys = sorted(set(item_dict.keys()) - set(scalar_keys))
        for remaining_key in remaining_keys:
            non_scalar.append((remaining_key, item_dict[remaining_key]))
    return scalar, non_scalar
