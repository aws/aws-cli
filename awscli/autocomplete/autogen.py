"""This module is used to auto-generate server side completion data.

This module can be used during the build process to generate any new
server side autocompletions based on updated service models.
It can also be used to regen completion data as new heuristics are added.

"""
import logging
from difflib import SequenceMatcher
from collections import namedtuple


LOG = logging.getLogger(__name__)
Resource = namedtuple('Resource', ['resource_name', 'ident_name',
                                   'operation', 'jp_expr'])


class ServerCompletionHeuristic(object):
    # Prefix that typically indicates listing resources,
    # e.g ListResources, DescribeResources, etc.
    _RESOURCE_VERB_PREFIX = ('get', 'list', 'describe')

    def __init__(self, singularize=None):
        if singularize is None:
            singularize = BasicSingularize()
        self._singularize = singularize

    def generate_completion_descriptions(self, service_model):
        """

        :param service_model: A botocore.model.ServiceModel.
        """
        # This method is a best-effort attempt at generating server side
        # auto-completion data based on a set of heuristics.  It's not
        # completely accurate and the results should be manually vetted.

        # candidate -> a potential operation that can be used to
        #   to describe a resource (e.g ListResources, DescribeResources)
        # non_candidate -> a potential operation that can use
        #   auto-completion data (e.g DeleteResource, UpdateResource)
        candidates = []
        non_candidates = []
        for op_name in service_model.operation_names:
            if op_name.lower().startswith(self._RESOURCE_VERB_PREFIX):
                candidates.append(op_name)
            else:
                non_candidates.append(op_name)
        all_resources = self._generate_resource_descriptions(
            candidates, service_model)
        all_operations = self._generate_operations(non_candidates,
                                                   all_resources,
                                                   service_model)
        return {
            'resources': all_resources,
            'operations': all_operations,
        }

    def _generate_resource_descriptions(self, candidates, service_model):
        all_resources = {}
        for op_name in candidates:
            resource = self._resource_for_single_operation(
                op_name, service_model)
            if resource is not None:
                self._inject_resource(all_resources, resource)
        return all_resources

    def _generate_operations(self, op_names, resources, service_model):
        # member_name -> resource
        reverse_mapping = {}
        for name, identifier_map in resources.items():
            for key in identifier_map['resourceIdentifier']:
                reverse_mapping[key] = name
        op_map = {}
        for op_name in op_names:
            self._add_completion_data_for_operation(
                op_map, op_name, service_model, reverse_mapping
            )
        return op_map

    def _add_completion_data_for_operation(self, op_map, op_name,
                                           service_model, reverse_mapping):
        op_model = service_model.operation_model(op_name)
        input_shape = op_model.input_shape
        if not input_shape:
            return
        for member in input_shape.members:
            member_name = self._find_matching_member_name(
                member, reverse_mapping)
            if member_name is None:
                return
            resource_name = reverse_mapping[member_name]
            op = op_map.setdefault(op_name, {})
            param = op.setdefault(member, {})
            param['completions'] = [
                {'parameters': {},
                 'resourceName': resource_name,
                 'resourceIdentifier': member}
            ]

    def _find_matching_member_name(self, member, reverse_mapping):
        # Try to find something in the reverse mapping that's close
        # to the member name.  This is really inefficient but this is
        # a build time step so we don't really care about perf.
        if member in reverse_mapping:
            return member
        matcher = SequenceMatcher()
        matcher.set_seq2(member)
        for candidate in reverse_mapping:
            matcher.set_seq1(candidate)
            match_ratio = matcher.ratio()
            if match_ratio > 0.9:
                return candidate

    def _inject_resource(self, all_resources, resource):
        r = all_resources.setdefault(resource.resource_name, {})
        r['operation'] = resource.operation
        ident = r.setdefault('resourceIdentifier', {})
        ident[resource.ident_name] = resource.jp_expr

    def _resource_for_single_operation(self, op_name, service_model):
        # This heuristic works if there's a List/Describe operation
        # that has only one shape in the output that's of type list.
        # It will then find that inspect that list member to find
        # the best guess at which identifier maps to the resource.
        # This is a best effort attempt and relies heavily on naming
        # conventions.
        op_model = service_model.operation_model(op_name)
        output = op_model.output_shape
        list_members = [member for member, shape in output.members.items()
                        if shape.type_name == 'list']
        if len(list_members) != 1:
            LOG.debug("Operation does not have exactly one list member, "
                      "skipping: %s (%s)", op_name, list_members)
            return
        resource_shape_name = list_members[0]
        list_member = output.members[resource_shape_name].member
        if list_member.type_name == 'structure':
            return self._resource_from_structure(
                op_name, resource_shape_name, list_member)
        elif list_member.type_name == 'string':
            return self._resource_from_string(
                op_name, resource_shape_name,
            )

    def _resource_from_structure(self, op_name,
                                 resource_shape_name, list_member):
        candidates = list_member.members
        op_with_prefix_removed = self._remove_verb_prefix(op_name)
        best_match = max(
            list(candidates),
            key=lambda x: SequenceMatcher(
                None, op_with_prefix_removed, x).ratio())
        singular_name = self._singularize.make_singular(
            op_with_prefix_removed)
        jp_expr = (
            '{resource_shape_name}[].{best_match}').format(
                resource_shape_name=resource_shape_name,
                best_match=best_match)
        r = Resource(singular_name, best_match, op_name, jp_expr)
        return r

    def _resource_from_string(self, op_name, resource_shape_name):
        op_with_prefix_removed = self._remove_verb_prefix(op_name)
        singular_name = self._singularize.make_singular(
            op_with_prefix_removed)
        r = Resource(singular_name, resource_shape_name, op_name,
                     '{resource_shape_name}[]'.format(
                         resource_shape_name=resource_shape_name))
        return r

    def _remove_verb_prefix(self, op_name):
        for prefix in self._RESOURCE_VERB_PREFIX:
            # 'ListResources' -> 'Resources'
            if op_name.lower().startswith(prefix):
                op_with_prefix_removed = op_name[len(prefix):]
                return op_with_prefix_removed


class BasicSingularize(object):
    """Simple implementation of making a word singular.

    Where possible, you should use nltk.stem.WordNetLemmatizer.
    It's not included here as a default to avoid a hard dependency
    on nltk.

    """

    def make_singular(self, name):
        # Certificates -> Certificate
        if name.endswith('ies'):
            return name[:-3] + 'y'
        elif name.endswith('es'):
            return name[:-1]
        elif name.endswith('s'):
            return name[:-1]
        else:
            return name
