# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import os
import json
import math


class TopicTagDB(object):
    """This class acts like a database for the tags of all available topics.

    A tag is an element in a topic reStructured text file that contains
    information about a topic. Information can range from titles to even
    related CLI commands. Here are all of the currently supported tags:

    Tag                 Meaning                         Required?
    ---                 -------                         ---------
    :title:             The title of the topic          Yes
    :description:       Sentence description of topic   Yes
    :category:          Category topic falls under      Yes
    :related topic:     A related topic                 No
    :related command:   A related command               No

    To see examples of how to specify tags looks in the directory
    awscli/topics. Note that tags can have multiple values by delimiting
    values with commas. All tags must be on their own line in the file.

    This class can load a JSON index represeting all of topics and their tags,
    scan all of the topics and store the values of their tags, retrieve the
    tag value for a particular topic, query for all the topics with a specific
    tag and/or value, and save the loaded data back out to a JSON index.

    The structure of the database can be viewed as a python dictionary:

    {'topic-name-1': {
        ':title:': ['My First Topic Title'],
        ':description:': ['This describes my first topic'],
        ':category:': ['General Topics', 'S3'],
        ':related command:': ['aws s3'],
        ':related topic:': ['topic-name-2']
     },
     'topic-name-2': { .....
    }

    The keys of the dictionary are the CLI command names of the topics. These
    names are based off the name of the reStructed text file that corresponds
    to the topic. The value of these keys are dictionary of tags, where the
    tags are keys and their values is a list of values for that tag. Note
    that all tag values for a specific tag of a specific topic are unique.
    """

    VALID_TAGS = [':category:', ':description:', ':title:', ':related topic:',
                  ':related command:']

    # The default directory to look for topics.
    TOPIC_DIR = os.path.join(
        os.path.dirname(
                os.path.abspath(__file__)), 'topics')

    # The default JSON index to load.
    JSON_INDEX = os.path.join(TOPIC_DIR, 'topic-tags.json')

    def __init__(self):
        self._tag_dictionary = {}

    def load_json_index(self, index_file=None):
        """Loads a JSON file into the tag dictionary.

        :param index_file: The path to a specific JSON index to load.
            If nothing is specified it will default to the default JSON
            index at ``JSON_INDEX``.
        """
        index_filepath = self.JSON_INDEX
        if index_file is not None:
            index_filepath = index_file
        with open(index_filepath, 'r') as f:
            index = f.read()
            self._tag_dictionary = json.loads(index)

    def save_to_json_index(self, index_file=None):
        """Writes the loaded data back out to the JSON index.

        :param index_file: The path to a specific JSON index to load.
            If nothing is specified it will default to the the default
            JSON index at ``JSON_INDEX``.
        """
        index_filepath = self.JSON_INDEX
        if index_file is not None:
            index_filepath = index_file
        with open(index_filepath, 'w') as f:
            f.write(json.dumps(self._tag_dictionary, indent=4, sort_keys=True))

    def get_all_topic_names(self):
        """Retrieves all of the topic names of the loaded JSON index"""
        return self._tag_dictionary.keys()

    def get_all_topic_src_files(self):
        """Retrieves the file paths of all the topics in directory"""
        topic_full_paths = []
        topic_names = os.listdir(self.TOPIC_DIR)
        for topic_name in topic_names:
            # Do not try to load hidden files.
            if not topic_name.startswith('.'):
                topic_full_path = os.path.join(self.TOPIC_DIR, topic_name)
                # Ignore the JSON Index as it is stored with topic files.
                if topic_full_path != self.JSON_INDEX:
                    topic_full_paths.append(topic_full_path)
        return topic_full_paths

    def scan(self, topic_files):
        """Scan in the tags of a list of topics into memory.

        Note that if there are existing values in an entry in the database
        of tags, they will not be overwritten. Any new values will be
        appended to original values.

        :param topic_files: A list of paths to topics to scan into memory.
        """
        for topic_file in topic_files:
            with open(topic_file, 'r') as f:
                # Parse out the name of the topic
                topic_name = self._find_topic_name(topic_file)
                # Add the topic to the dictionary if it does not exist
                self._add_topic_name_to_dict(topic_name)
                for line in f.readlines():
                    # Iterate over each line, detect if the line
                    # is a tag, and retrieve the tag and value if is.
                    tag, values = self._retrieve_tag_and_values(line)
                    if tag is not None:
                        # Add the tag and value to the dictionary if
                        # a tag is detected.
                        self._add_tag_to_dict(topic_name, tag, values)

    def _find_topic_name(self, topic_src_file):
        # Get the name of each of these files
        topic_name_with_ext = os.path.basename(topic_src_file)
        # Strip of the .rst extension from the files
        return topic_name_with_ext[:-4]

    def _retrieve_tag_and_values(self, line):
        # This method retrieves the tag and associated value of a line. If
        # the line is not a tag, ``None`` is returned for both.

        for valid_tag in self.VALID_TAGS:
            if line.startswith(valid_tag):
                value = self._retrieve_values_from_tag(line, valid_tag)
                return valid_tag, value
        return None, None

    def _retrieve_values_from_tag(self, line, tag):
        # This method retrieves the value from a tag. Tags with multiple
        # values will be seperated by commas. All values will be returned
        # as a list.

        # First remove the tag.
        line = line.lstrip(tag)
        # Remove surrounding whitespace from value
        line = line.strip()
        # Find all values associated to the tag. Values are seperated by
        # commas.
        values = line.split(',')
        # Strip the white space from each of these values.
        for i in range(len(values)):
            values[i] = values[i].strip()
        return values

    def _add_topic_name_to_dict(self, topic_name):
        # This method adds a topic name to the dictionary if it does not
        # already exist

        # Check if the topic is in the topic tag dictionary
        if self._tag_dictionary.get(topic_name, None) is None:
            self._tag_dictionary[topic_name] = {}

    def _add_tag_to_dict(self, topic_name, tag, values):
        # This method adds a tag to the dictionary given its tag and value
        # If there are existing values associated to the tag it will add
        # only values that previously did not exist in the list.

        # Check if the topic is in the topic tag dictionary
        self._add_topic_name_to_dict(topic_name)
        # Get all of a topics tags
        topic_tags = self._tag_dictionary[topic_name]
        self._add_key_values(topic_tags, tag, values)

    def _add_key_values(self, dictionary, key, values):
        # This method adds a value to a dictionary given a key.
        # If there are existing values associated to the key it will add
        # only values that previously did not exist in the list. All values
        # in the dictionary should be lists

        if dictionary.get(key, None) is None:
            dictionary[key] = []
        for value in values:
            if value not in dictionary[key]:
                dictionary[key].append(value) 

    def query(self, tag, values=None):
        """Groups topics by a specific tag and/or tag value.

        :param tag: The name of the tag to query for.
        :param values: A list of tag values to include.

        :rtype: dictionary
        :returns: A dictionary whose keys are all possible tag values and the
            keys' values are all of the topic names that had that tag value
            in its source file. For example, if ``topic-name-1`` had the tag
            ``:category: foo, bar`` and ``topic-name-2`` had the tag
            ``:category: foo`` and we queried based on :category:, the returned
            dictionary would be:

            {
             'foo': ['topic-name-1', 'topic-name-2'],
             'bar': ['topic-name-1']
            }

        """
        query_dict = {}
        for topic_name in self._tag_dictionary.keys():
            # Get the tag values for a specified tag of the topic
            if self._tag_dictionary[topic_name].get(tag, None) is not None:
                tag_values = self._tag_dictionary[topic_name][tag]
                for tag_value in tag_values:
                    # Add the values to dictionary to be returned if
                    # no value constraints are provided or if the tag value
                    # falls in the allowed tag values.
                    if values is None or tag_value in values:
                        self._add_key_values(query_dict,
                                             key=tag_value,
                                             values=[topic_name])
        return query_dict 
        

    def get_tag_value(self, topic_name, tag, default_value=None):
        """Get a value of a tag for a topic

        :param topic_name: The name of the topic
        :param tag: The name of the tag to retrieve
        :param default_value: The value to return if the topic and/or tag
            does not exist.
        """
        if topic_name in self._tag_dictionary:
            return self._tag_dictionary[topic_name].get(tag, default_value)
        return default_value

    def _line_has_tag(self, line):
        for valid_tag in self.VALID_TAGS:
            if line.startswith(valid_tag):
                return True
        return False
