from neo4j import GraphDatabase
import logging

logging.getLogger("neo4j").setLevel(logging.ERROR)

class Interface:
    def __init__(self, uri, user, password):
        self._driver = GraphDatabase.driver(uri, auth=(user, password), encrypted=False)
        self._driver.verify_connectivity()

    def close(self):
        self._driver.close()

    def bfs(self, start_node, last_node):
        with self._driver.session() as session:
            check_bfs_graph = "CALL gds.graph.exists('bfs_graph') YIELD exists RETURN exists"

            if session.run(check_bfs_graph).single()["exists"]:
                drop_bfs_graph = """
                CALL gds.graph.drop('bfs_graph');
                """
                session.run(drop_bfs_graph)
            
            create_bfs_graph = """
            MATCH (source:Location)-[r:TRIP]->(target:Location)
            RETURN gds.graph.project(
              'bfs_graph',
              source,
              target
            );
            """
            session.run(create_bfs_graph)

            bfs_query = """
            MATCH (source:Location{name:$start_node}), (target:Location{name:$last_node})
            WITH source, [target] AS targetNodes
            CALL gds.bfs.stream('bfs_graph', {
                sourceNode: source,
                targetNodes: targetNodes
            })
            YIELD path
            RETURN [node IN nodes(path)] AS path
            """
            result = session.run(bfs_query, parameters={"start_node": start_node, "last_node": last_node})
            return [{"path": record["path"]} for record in result]

    def pagerank(self, max_iterations, weight_property):
        with self._driver.session() as session:
            check_pagerank_graph = "CALL gds.graph.exists('pagerank_graph') YIELD exists RETURN exists"

            if session.run(check_pagerank_graph).single()["exists"]:
                drop_pagerank_graph = """
                CALL gds.graph.drop('pagerank_graph');
                """
                session.run(drop_pagerank_graph)
            
            create_pagerank_graph = """
            MATCH (source:Location)-[r:TRIP]->(target:Location)
            RETURN gds.graph.project(
              'pagerank_graph',
              source,
              target,
              { relationshipProperties: r { .distance } }
            );
            """
            session.run(create_pagerank_graph)

            pagerank_query = """
            CALL gds.pageRank.stream('pagerank_graph', {
                maxIterations: $max_iterations,
                relationshipWeightProperty: $weight_property
            })
            YIELD nodeId, score
            RETURN gds.util.asNode(nodeId) AS node, score
            ORDER BY score DESC
            """
            result = session.run(pagerank_query, parameters={"max_iterations": max_iterations, "weight_property": weight_property})
            nodes = [record for record in result]

            if not nodes:
                return None

            max_pagerank = {"name": nodes[0]["node"]["name"], "score": nodes[0]["score"]}
            min_pagerank = {"name": nodes[-1]["node"]["name"], "score": nodes[-1]["score"]}

            return [max_pagerank, min_pagerank]
