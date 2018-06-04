"""Category operations used by neo4j graph rewriting tool."""

import regraph.neo4j.cypher_utils as cypher


def pullback(b, c, d, a=None, inplace=False):
    """Find the pullback from b -> d <- c."""
    if a is None:
        a = "pb_" + "_".join([b, c, d])
    query = ""
    carry_vars = set()

    # Match all the pair of nodes with the same image in d
    query +=\
        "OPTIONAL MATCH (n:{})-[:typing]->(:{})<-[:typing]-(m:{})\n".format(
            b, d, c)

    # For each pair, collect all the merged properties
    query += cypher.merge_properties(["n", "m"], 'new_props',
                                     method='intersection',
                                     carry_vars=carry_vars)
    # For each pair, create a new node
    query += cypher.create_node(
                        var_name="new_node_a",
                        node_id="pb",
                        node_id_var="id_var",
                        label=a,
                        carry_vars=carry_vars,
                        ignore_naming=True)[0]
    carry_vars.remove("id_var")
    query += "SET new_node_a += new_props\n"
    carry_vars.remove("new_props")

    # Add the typing edges
    query += cypher.with_vars(carry_vars) + "\n"
    query += cypher.create_edge('new_node_a', 'n', edge_label='typing') + "\n"
    query += cypher.create_edge('new_node_a', 'm', edge_label='typing') + "\n"

    # Add the graph edges
    carry_vars = set()
    query2 = ""
    query2 +=\
        "MATCH (x:{})-[:typing]->(:{})-[r1:edge]->(:{})<-[:typing]-(y:{}),\n".format(
            a, b, b, a) +\
        "(x)-[:typing]->(:{})-[r2:edge]->(:{})<-[:typing]-(y)\n".format(
            c, c)
    # Collect all the merged properties of the edges r1 and r2
    query2 += cypher.merge_properties(["r1", "r2"], 'new_props',
                                      method='intersection',
                                      carry_vars={'x', 'y'})
    query2 += "MERGE (x)-[r:edge]->(y)\n"
    query2 += "SET r += new_props"

    return query, query2


def pushout(a, b, c, d=None, inplace=False):
    pass


def pullback_complement(a, b, d, c=None, inplace=False):
    pass


def check_homomorphism(domain, codomain, total=True):
    pass