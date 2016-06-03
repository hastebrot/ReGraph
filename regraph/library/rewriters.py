"""."""
import networkx as nx
from networkx.algorithms import isomorphism

import itertools

from regraph.library.parser import parser
from regraph.library.primitives import (merge_nodes,
                                        clone_node,
                                        add_node,
                                        remove_node,
                                        add_edge,
                                        remove_edge)
from regraph.library.utils import is_subdict
from regraph.library.data_structures import (TypedDiGraph,
                                             Homomorphism)


class Rewriter:
    """Class implements the transformation on the graph."""

    def __init__(self, graph):
        """Initialize Rewriter object with input graph."""
        self.graph_ = graph
        self.parser_ = parser
        return

    def find_matching(self, pattern):
        """Perform matching of the pattern graph."""
        matching_nodes = set()
        # find all the nodes matching the nodes in pattern
        for pattern_node in pattern.nodes():
            for node in self.graph_.nodes():
                if pattern.node[pattern_node].type_ == self.graph_.node[node].type_:
                    if is_subdict(pattern.node[pattern_node].attrs_,
                                  self.graph_.node[node].attrs_):
                        matching_nodes.add(node)

        reduced_graph = self.graph_.subgraph(matching_nodes)
        instances = []
        isomorphic_subgraphs = []
        for sub_nodes in itertools.combinations(reduced_graph.nodes(),
                                                len(pattern.nodes())):
                subg = reduced_graph.subgraph(sub_nodes)
                for edgeset in itertools.combinations(subg.edges(),
                                                      len(pattern.edges())):
                    edge_induced_graph = nx.DiGraph(edgeset)
                    GM = isomorphism.GraphMatcher(pattern, edge_induced_graph)
                    if GM.is_isomorphic():
                        isomorphic_subgraphs.append((subg, GM.mapping))

        for subgraph, mapping in isomorphic_subgraphs:
            # check node matches
            # exclude subgraphs which nodes information does not
            # correspond to pattern
            for (pattern_node, node) in mapping.items():
                if not pattern.node[pattern_node].type_ == subgraph.node[node].type_:
                    break
                if not is_subdict(pattern.node[pattern_node].attrs_, subgraph.node[node].attrs_):
                    break
            else:
                # check edge attribute matched
                for edge in pattern.edges():
                    pattern_attrs = pattern.get_edge(edge[0], edge[1])
                    target_attrs = subgraph.get_edge(mapping[edge[0]], mapping[edge[1]])
                    if not is_subdict(pattern_attrs, target_attrs):
                        break
                else:
                    instances.append(mapping)
        return instances

    def clone(self, instance, node, name=None):
        if node in instance.keys():
            print("Hello")
            new_name = clone_node(self.graph_, instance[node], name)
        else:
            new_name = clone_node(self.graph_, node, name)
        return new_name

    def merge(self, instance, nodes, method=None,
              node_name=None, edges_method=None):
        nodes_to_merge =\
            [instance[n] if n in instance.keys() else n
             for n in nodes]
        new_name = merge_nodes(
            self.graph_,
            nodes_to_merge,
            method,
            node_name)
        return new_name

    def add_node(self, instance, node_type, name=None, attrs={}):
        new_name = add_node(self.graph_, node_type, name, attrs)
        return new_name

    def delete_node(self, instance, node):
        if node in instance.keys():
            remove_node(self.graph_, instance[node])
        else:
            remove_node(self.graph_, node)
        return

    def add_edge(self, instance, node_1, node_2, attrs={}):
        if node_1 in instance.keys():
            source = instance[node_1]
        else:
            source = node_1
        if node_2 in instance.keys():
            target = instance[node_2]
        else:
            target = node_2
        add_edge(self.graph_, source, target, attrs)
        return

    def delete_edge(self, instance, node_1, node_2):
        if node_1 in instance.keys():
            source = instance[node_1]
        else:
            source = node_1
        if node_2 in instance.keys():
            target = instance[node_2]
        else:
            target = node_2
        remove_edge(self.graph_, source, target)

    def transform_instance(self, instance, commands):
        """Transform the instance of LHS of the rule in the graph."""
        # for node in self.graph_.nodes():
        #     print(self.graph_.node[node].type_)
        command_strings = [c for c in commands.splitlines() if len(c) > 0]
        for command in command_strings:
            try:
                parsed = parser.parseString(command).asDict()
                if parsed["keyword"] == "clone":
                    node_name = None
                    if "node_name" in parsed.keys():
                        node_name = parsed["node_name"]
                    self.clone(instance, parsed["node"], node_name)
                elif parsed["keyword"] == "merge":
                    method = None
                    node_name = None
                    edges_method = None
                    if "method" in parsed.keys():
                        method = parsed["method"]
                    if "node_name" in parsed.keys():
                        node_name = parsed["node_name"]
                    if "edges_method" in parsed.keys():
                        edges_method = parsed["edges_method"]
                    self.merge(
                        instance,
                        parsed["nodes"],
                        method,
                        node_name,
                        edges_method)
                elif parsed["keyword"] == "add_node":
                    name = None
                    node_type = None
                    attrs = {}
                    if "node" in parsed.keys():
                        name = parsed["node"]
                    if "type" in parsed.keys():
                        node_type = parsed["type"]
                    if "attrubutes" in parsed.keys():
                        attrs = parsed["attrubutes"]
                    self.add_node(node_type, name, attrs)
                elif parsed["keyword"] == "delete_node":
                    self.delete_node(instance, parsed["node"])
                elif parsed["keyword"] == "add_edge":
                    attrs = {}
                    if "attrubutes" in parsed.keys():
                        attrs = parsed["attrubutes"]
                    self.add_edge(instance, parsed["node_1"], parsed["node_2"], attrs)
                elif parsed["keyword"] == "delete_edge":
                    self.delete_edge(instance, parsed["node_1"], parsed["node_2"])
                else:
                    raise ValueError("Unknown command")
            except:
                raise ValueError("Cannot parse command '%s'" % command)

    def apply_rule(self, instance, left_h, right_h):

        # check left_h.source == right_h.source
        if left_h.source_.nodes() != right_h.source_.nodes():
            raise ValueError("Preserving part does not match!")
        if left_h.source_.edges() != right_h.source_.edges():
            raise ValueError("Preserving part does not match!")

        RHS_instance =\
            dict([(r, instance[left_h.mapping_[p]]) for p, r in right_h.mapping_.items()])

        # 0) fetch attributes for nodes
        for p, r in right_h.mapping_.items():
            for key, value in right_h.target_.node[r].attrs_.items():
                node_id = instance[left_h.mapping_[p]]
                self.graph_.node[node_id].attrs_.update({key: value})

        for s, t in right_h.source_.edges():
            s_from_r = right_h.mapping_[s]
            t_from_r = right_h.mapping_[t]
            for key, value in right_h.target_.edge[s_from_r][t_from_r].items():
                left_h.target_.edge[left_h.mapping_[s]][left_h.mapping_[t]].update({key: value})

        # 1) find final PBC
        (nodes_to_remove, edges_to_remove) = left_h.find_final_PBC()

        for edge in edges_to_remove:
            self.delete_edge(instance, edge[0], edge[1])
        for node in nodes_to_remove:
            self.delete_node(instance, node)

        # 2) find push-out
        (nodes_to_add, edges_to_add) = right_h.find_PO()

        for node in nodes_to_add:
            new_name = self.add_node(
                instance,
                right_h.target_.node[node].type_,
                attrs=right_h.target_.node[node].attrs_)
            RHS_instance.update({node: new_name})

        for s, t, attrs in edges_to_add:
            try:
                self.add_edge(
                    instance,
                    left_h.mapping_[s],
                    left_h.mapping_[t],
                    attrs)
            except:
                for key, value in attrs.items():
                    self.graph_.edge[left_h.mapping_[s]][left_h.mapping_[t]].update({key: value}) 

        # 3) find nodes to merge
        merge_dict = {}
        for n in right_h.target_.nodes():
            merge_dict.update({n: []})
        for p_node, r_node in right_h.mapping_.items():
            if left_h.mapping_[p_node] not in nodes_to_remove:
                merge_dict[r_node].append(left_h.mapping_[p_node])

        nodes_to_merge = [(key, value) for key, value in merge_dict.items() if len(value) > 1]

        for rhs_node, nodes in nodes_to_merge:
            new_name = self.merge(instance, nodes)
            RHS_instance.update({rhs_node: new_name})

        # 4) find nodes to clone
        clone_dict = {}
        for n in left_h.target_.nodes():
            clone_dict.update({n: []})
        for p_node, r_node in left_h.mapping_.items():
            clone_dict[r_node].append(p_node)

        nodes_to_clone = [(key, len(value)) for key, value in clone_dict.items() if len(value) > 1]

        for node, times in nodes_to_clone:
            for i in range(times):
                new_name = self.clone(instance, node)
                # RHS_instance.update({ node: })

        return RHS_instance


    def rule_to_homomorphisms(self, LHS, commands):
        """Cast sequence of commands to homomorphisms."""
        command_strings = [c for c in commands.splitlines() if len(c) > 0]
        actions = []
        for command in command_strings:
            try:
                parsed = parser.parseString(command).asDict()
                actions.append(parsed)
            except:
                raise ValueError("Cannot parse command '%s'" % command)

        P = LHS.copy()
        RHS = LHS.copy()

        pl_mapping = dict(zip(LHS.nodes(), LHS.nodes()))
        pr_mapping = dict(zip(LHS.nodes(), LHS.nodes()))
        # We modify P, RHS and respective mapping
        # in the course of command parsing
        for action in actions:
            if action["keyword"] == "clone":
                node_name = None
                if "node_name" in action.keys():
                    node_name = action["node_name"]
                cloned_node = clone_node(P, action["node"], node_name)
                pl_mapping[action["node"]] = action["node"]
                pl_mapping.update({cloned_node: action["node"]})
                clone_node(RHS, action["node"], node_name)
            elif action["keyword"] == "merge":
                method = None
                node_name = None
                edges_method = None
                if "method" in action.keys():
                    method = action["method"]
                if "node_name" in action.keys():
                    node_name = action["node_name"]
                if "edges_method" in action.keys():
                    edges_method = action["edges_method"]
                merged_node = merge_nodes(
                    RHS,
                    action["nodes"],
                    method,
                    node_name,
                    edges_method)
                for node in action["nodes"]:
                    pr_mapping.update({node: merged_node})
            elif action["keyword"] == "add_node":
                name = None
                node_type = None
                attrs = {}
                if "node" in action.keys():
                    name = action["node"]
                if "type" in action.keys():
                    node_type = action["type"]
                if "attrubutes" in action.keys():
                    attrs = action["attrubutes"]
                add_node(RHS, node_type, name, attrs)
            elif action["keyword"] == "delete_node":
                remove_node(P, action["node"])
                del pl_mapping[action["node"]]
                del pr_mapping[action["node"]]
                remove_node(RHS, action["node"])
            elif action["keyword"] == "add_edge":
                attrs = {}
                if "attrubutes" in action.keys():
                    attrs = action["attrubutes"]
                add_edge(
                    RHS,
                    action["node_1"],
                    action["node_2"],
                    attrs)
            elif action["keyword"] == "delete_edge":
                remove_edge(
                    P,
                    action["node_1"],
                    action["node_2"])
                remove_edge(
                    RHS,
                    action["node_1"],
                    action["node_2"])
            else:
                raise ValueError("Unknown command")
        print(P.nodes())
        print(LHS.nodes())
        print(RHS.nodes())
        print(pl_mapping)
        print(pr_mapping)
        h_p_lhs = Homomorphism(P, LHS, pl_mapping)
        h_p_rhs = Homomorphism(P, RHS, pr_mapping)
        return (h_p_lhs, h_p_rhs)