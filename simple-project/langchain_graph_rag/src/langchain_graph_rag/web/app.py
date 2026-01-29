"""
Flask web application for graph knowledge visualization.

Provides REST API and web interface for exploring MySQL table relationships.
"""

import os
import asyncio
from typing import Dict, Any
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from loguru import logger
from ..services.graph_service import GraphQueryService
from ..graph.neo4j_store import Neo4jGraphStore
from ..llm.langchain_llm import get_default_llm
from ..agents.path_agent import PathQueryAgent
from ..utils.logger import setup_logger

# Initialize Flask app
app = Flask(__name__,
            template_folder='templates',
            static_folder='static')
CORS(app)

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'graph-rag-secret-key')

# Global service instances (initialized later)
graph_service: GraphQueryService = None
path_agent: PathQueryAgent = None


def init_services():
    """Initialize graph services on startup."""
    global graph_service, path_agent

    # Setup logger
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    log_file = os.getenv('LOG_FILE', 'logs/app.log')
    setup_logger(log_level=log_level, log_file=log_file)

    # Get Neo4j configuration
    neo4j_uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    neo4j_user = os.getenv('NEO4J_USER', 'neo4j')
    neo4j_password = os.getenv('NEO4J_PASSWORD', 'password')

    # Initialize graph store
    try:
        graph_store = Neo4jGraphStore(
            uri=neo4j_uri,
            user=neo4j_user,
            password=neo4j_password
        )
        asyncio.run(graph_store.initialize())

        # Initialize graph service
        graph_service = GraphQueryService(graph_store=graph_store)

        # Initialize LLM and agent
        try:
            llm = get_default_llm()
            path_agent = PathQueryAgent(
                name="PathQueryAgent",
                llm=llm,
                graph_service=graph_service
            )
            logger.info("Path agent initialized successfully")
        except Exception as e:
            logger.warning(f"Could not initialize LLM agent: {e}")

        logger.info("Graph services initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize graph services: {e}")
        raise


# ============================================================================
# Web Routes
# ============================================================================

@app.route('/')
def index():
    """Main page - graph visualization."""
    return render_template('index.html')


@app.route('/query')
def query_page():
    """Query page - path and neighbor queries."""
    return render_template('query.html')


# ============================================================================
# API Routes
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "graph-rag",
        "graph_service_initialized": graph_service is not None
    })


@app.route('/api/graph/nodes', methods=['GET'])
def get_nodes():
    """Get all nodes in the graph."""
    try:
        nodes = asyncio.run(graph_service.get_all_nodes())
        return jsonify({
            "success": True,
            "data": [node.model_dump() for node in nodes],
            "count": len(nodes)
        })
    except Exception as e:
        logger.error(f"Error getting nodes: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/graph/edges', methods=['GET'])
def get_edges():
    """Get all edges in the graph."""
    try:
        edges = asyncio.run(graph_service.get_all_edges())
        return jsonify({
            "success": True,
            "data": [edge.model_dump() for edge in edges],
            "count": len(edges)
        })
    except Exception as e:
        logger.error(f"Error getting edges: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/graph/path', methods=['POST'])
def find_path():
    """Find path between two tables."""
    try:
        data = request.json
        start_table = data.get('start_table')
        end_table = data.get('end_table')
        max_hops = data.get('max_hops', 5)
        use_llm = data.get('use_llm_explanation', True)

        if not start_table or not end_table:
            return jsonify({
                "success": False,
                "error": "Missing start_table or end_table"
            }), 400

        if path_agent and use_llm:
            result = asyncio.run(path_agent.find_path(
                start_table=start_table,
                end_table=end_table,
                max_hops=max_hops
            ))
        else:
            result = asyncio.run(graph_service.find_path_with_explanation(
                start_table=start_table,
                end_table=end_table,
                max_hops=max_hops
            ))

        return jsonify({
            "success": True,
            "data": result
        })

    except Exception as e:
        logger.error(f"Error finding path: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/graph/neighbors', methods=['POST'])
def find_neighbors():
    """Find neighbors of a table."""
    try:
        data = request.json
        table_name = data.get('table_name')
        depth = data.get('depth', 1)
        include_relations = data.get('include_relations', True)

        if not table_name:
            return jsonify({
                "success": False,
                "error": "Missing table_name"
            }), 400

        if include_relations:
            result = asyncio.run(graph_service.find_neighbors_with_relations(
                table_name=table_name,
                depth=depth
            ))
        else:
            neighbors = asyncio.run(graph_service.find_neighbors(
                table_name=table_name,
                depth=depth
            ))
            result = {
                "center_table": table_name,
                "neighbors": [
                    {"table": n.id.replace("table:", ""), "label": n.label}
                    for n in neighbors
                ],
                "total_count": len(neighbors)
            }

        return jsonify({
            "success": True,
            "data": result
        })

    except Exception as e:
        logger.error(f"Error finding neighbors: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/graph/statistics', methods=['GET'])
def get_statistics():
    """Get graph statistics."""
    try:
        stats = asyncio.run(graph_service.get_statistics())
        return jsonify({
            "success": True,
            "data": stats.model_dump()
        })
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/graph/relations/<table_name>', methods=['GET'])
def get_table_relations(table_name: str):
    """Get all relations for a specific table."""
    try:
        direction = request.args.get('direction', 'both')
        relations = asyncio.run(graph_service.get_relations_for_table(
            table_name=table_name,
            direction=direction
        ))
        return jsonify({
            "success": True,
            "data": relations,
            "count": len(relations)
        })
    except Exception as e:
        logger.error(f"Error getting relations: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/graph/search', methods=['GET', 'POST'])
def search_tables():
    """Search tables by name, column, or comment."""
    try:
        # Support both GET and POST
        if request.method == 'GET':
            query = request.args.get('q', '')
        else:
            data = request.json
            query = data.get('q', '') if data else ''

        if not query:
            return jsonify({
                "success": False,
                "error": "Missing search query 'q'"
            }), 400

        query_lower = query.lower()
        nodes = asyncio.run(graph_service.get_all_nodes())

        matches = []
        for node in nodes:
            node_dict = node.model_dump()
            props = node_dict.get('properties', {})

            # Search in table name
            if query_lower in node.label.lower() or query_lower in node.id.lower():
                matches.append(node_dict)
                continue

            # Search in columns
            columns = props.get('columns', [])
            for col in columns:
                if (query_lower in col.get('name', '').lower() or
                    query_lower in col.get('type', '').lower() or
                    query_lower in col.get('comment', '').lower() or
                    any(query_lower in alias.lower() for alias in col.get('aliases', []))):
                    matches.append(node_dict)
                    break

            # Search in table comment
            if query_lower in props.get('comment', '').lower():
                matches.append(node_dict)
                continue

            # Search in semantic labels
            semantic_labels = props.get('semantic_labels', [])
            for label in semantic_labels:
                if query_lower in label.lower():
                    matches.append(node_dict)
                    break

        return jsonify({
            "success": True,
            "data": matches,
            "count": len(matches),
            "query": query
        })

    except Exception as e:
        logger.error(f"Error searching tables: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================================
# Error Handlers
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({
        "success": False,
        "error": "Not found"
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {error}")
    return jsonify({
        "success": False,
        "error": "Internal server error"
    }), 500


# ============================================================================
# Main
# ============================================================================

def main():
    """Main entry point."""
    # Initialize services
    init_services()

    # Get configuration
    host = os.getenv('APP_HOST', '0.0.0.0')
    port = int(os.getenv('APP_PORT', 5001))
    debug = os.getenv('APP_DEBUG', 'True').lower() == 'true'

    # Run app
    logger.info(f"Starting Flask app on {host}:{port}")
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    main()
