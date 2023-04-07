# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

import os
import yaml
import logging
import errno
from botocore.compat import OrderedDict

from awscli.customizations.eks.exceptions import EKSError
from awscli.customizations.eks.ordered_yaml import (ordered_yaml_load,
                                                    ordered_yaml_dump)


class KubeconfigError(EKSError):
    """ Base class for all kubeconfig errors."""


class KubeconfigCorruptedError(KubeconfigError):
    """ Raised when a kubeconfig cannot be parsed."""


class KubeconfigInaccessableError(KubeconfigError):
    """ Raised when a kubeconfig cannot be opened for read/writing."""


def _get_new_kubeconfig_content():
    return OrderedDict([
        ("apiVersion", "v1"),
        ("clusters", []),
        ("contexts", []),
        ("current-context", ""),
        ("kind", "Config"),
        ("preferences", OrderedDict()),
        ("users", [])
    ])


class Kubeconfig(object):
    def __init__(self, path, content=None):
        self.path = path
        if content is None:
            content = _get_new_kubeconfig_content()
        self.content = content

    def dump_content(self):
        """ Return the stored content in yaml format. """
        return ordered_yaml_dump(self.content)

    def has_cluster(self, name):
        """
        Return true if this kubeconfig contains an entry
        For the passed cluster name.
        """
        if self.content.get('clusters') is None:
            return False
        return name in [cluster['name']
                        for cluster in self.content['clusters'] if 'name' in cluster]


class KubeconfigValidator(object):
    def __init__(self):
        # Validation_content is an empty Kubeconfig
        # It is used as a way to know what types different entries should be
        self._validation_content = Kubeconfig(None, None).content

    def validate_config(self, config):
        """
        Raises KubeconfigCorruptedError if the passed content is invalid

        :param config: The config to validate
        :type config: Kubeconfig
        """
        if not isinstance(config, Kubeconfig):
            raise KubeconfigCorruptedError("Internal error: "
                                           f"Not a {Kubeconfig}.")
        self._validate_config_types(config)
        self._validate_list_entry_types(config)

    def _validate_config_types(self, config):
        """
        Raises KubeconfigCorruptedError if any of the entries in config
        are the wrong type

        :param config: The config to validate
        :type config: Kubeconfig
        """
        if not isinstance(config.content, dict):
            raise KubeconfigCorruptedError(f"Content not a {dict}.")
        for key, value in self._validation_content.items():
            if (key in config.content and
                    config.content[key] is not None and
                    not isinstance(config.content[key], type(value))):
                raise KubeconfigCorruptedError(
                    f"{key} is wrong type: {type(config.content[key])} "
                    f"(Should be {type(value)})"
                )

    def _validate_list_entry_types(self, config):
        """
        Raises KubeconfigCorruptedError if any lists in config contain objects
        which are not dictionaries

        :param config: The config to validate
        :type config: Kubeconfig
        """
        for key, value in self._validation_content.items():
            if (key in config.content and
                    type(config.content[key]) == list):
                for element in config.content[key]:
                    if not isinstance(element, OrderedDict):
                        raise KubeconfigCorruptedError(
                            f"Entry in {key} not a {dict}. ")


class KubeconfigLoader(object):
    def __init__(self, validator = None):
        if validator is None:
            validator=KubeconfigValidator()
        self._validator=validator

    def load_kubeconfig(self, path):
        """
        Loads the kubeconfig found at the given path.
        If no file is found at the given path,
        Generate a new kubeconfig to write back.
        If the kubeconfig is valid, loads the content from it.
        If the kubeconfig is invalid, throw the relevant exception.

        :param path: The path to load a kubeconfig from
        :type path: string

        :raises KubeconfigInaccessableError: if the kubeconfig can't be opened
        :raises KubeconfigCorruptedError: if the kubeconfig is invalid

        :return: The loaded kubeconfig
        :rtype: Kubeconfig
        """
        try:
            with open(path, "r") as stream:
                loaded_content=ordered_yaml_load(stream)
        except IOError as e:
            if e.errno == errno.ENOENT:
                loaded_content=None
            else:
                raise KubeconfigInaccessableError(
                    f"Can't open kubeconfig for reading: {e}")
        except yaml.YAMLError as e:
            raise KubeconfigCorruptedError(
                f"YamlError while loading kubeconfig: {e}")

        loaded_config=Kubeconfig(path, loaded_content)
        self._validator.validate_config(loaded_config)

        return loaded_config


class KubeconfigWriter(object):
    def write_kubeconfig(self, config):
        """
        Write config to disk.
        OK if the file doesn't exist.

        :param config: The kubeconfig to write
        :type config: Kubeconfig

        :raises KubeconfigInaccessableError: if the kubeconfig
        can't be opened for writing
        """
        directory=os.path.dirname(config.path)

        try:
            os.makedirs(directory)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise KubeconfigInaccessableError(
                    f"Can't create directory for writing: {e}")
        try:
            with os.fdopen(
                    os.open(
                        config.path,
                        os.O_CREAT | os.O_RDWR | os.O_TRUNC,
                        0o600),
                    "w+") as stream:
                ordered_yaml_dump(config.content, stream)
        except (IOError, OSError) as e:
            raise KubeconfigInaccessableError(
                f"Can't open kubeconfig for writing: {e}")


class KubeconfigAppender(object):
    def insert_entry(self, config, key, new_entry):
        """
        Insert entry into the entries list at content[key]
        Overwrite an existing entry if they share the same name

        :param config: The kubeconfig to insert an entry into
        :type config: Kubeconfig
        """
        entries=self._setdefault_existing_entries(config, key)
        same_name_index=self._index_same_name(entries, new_entry)
        if same_name_index is None:
            entries.append(new_entry)
        else:
            entries[same_name_index]=new_entry
        return config

    def _setdefault_existing_entries(self, config, key):
        config.content[key]=config.content.get(key) or []
        entries=config.content[key]
        if not isinstance(entries, list):
            raise KubeconfigError(f"Tried to insert into {key}, "
                                  f"which is a {type(entries)} "
                                  f"not a {list}")
        return entries

    def _index_same_name(self, entries, new_entry):
        if "name" in new_entry:
            name_to_search=new_entry["name"]
            for i, entry in enumerate(entries):
                if "name" in entry and entry["name"] == name_to_search:
                    return i
        return None

    def _make_context(self, cluster, user, alias = None):
        """ Generate a context to associate cluster and user with a given alias."""
        return OrderedDict([
            ("context", OrderedDict([
                ("cluster", cluster["name"]),
                ("user", user["name"])
            ])),
            ("name", alias or user["name"])
        ])

    def insert_cluster_user_pair(self, config, cluster, user, alias = None):
        """
        Insert the passed cluster entry and user entry,
        then make a context to associate them
        and set current-context to be the new context.
        Returns the new context

        :param config: the Kubeconfig to insert the pair into
        :type config: Kubeconfig

        :param cluster: the cluster entry
        :type cluster: OrderedDict

        :param user: the user entry
        :type user: OrderedDict

        :param alias: the alias for the context; defaults top user entry name
        :type context: str

        :return: The generated context
        :rtype: OrderedDict
        """
        context=self._make_context(cluster, user, alias = alias)
        self.insert_entry(config, "clusters", cluster)
        self.insert_entry(config, "users", user)
        self.insert_entry(config, "contexts", context)

        config.content["current-context"]=context["name"]

        return context
