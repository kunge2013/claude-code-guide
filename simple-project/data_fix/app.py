"""
SQL Query Tool - Flask Web Application

A web-based GUI application to query MySQL database with three SQL templates
based on PROD_INST_ID input.

Usage:
    python app.py
"""
import json
import os
from datetime import datetime, date
from collections import OrderedDict
from flask import Flask, render_template, request, jsonify
from src.database.connection import ConnectionManager
from src.database.queries import QueryManager

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

# Custom JSON encoder that preserves dict order
class OrderedJSONEncoder(json.JSONEncoder):
    def encode(self, obj):
        if isinstance(obj, dict):
            # Use OrderedDict to preserve order during serialization
            return json.dumps(obj, ensure_ascii=False)
        return super().encode(obj)

app.json_encoder = OrderedJSONEncoder

# Initialize database managers
conn_manager = ConnectionManager()
query_manager = QueryManager(conn_manager)


def format_datetime_result(data):
    """Format datetime objects to YYYY-MM-DD HH:MM:SS format and handle Decimal types."""
    from collections import OrderedDict
    from decimal import Decimal

    if isinstance(data, list):
        return [format_datetime_result(row) for row in data]
    elif isinstance(data, dict):
        # Preserve the order of keys from the input dict
        is_ordered = isinstance(data, OrderedDict)
        formatted = OrderedDict() if is_ordered else {}
        for key, value in data.items():
            if isinstance(value, datetime):
                formatted[key] = value.strftime('%Y-%m-%d %H:%M:%S')
            elif isinstance(value, date):
                formatted[key] = value.strftime('%Y-%m-%d')
            elif isinstance(value, Decimal):
                # Convert Decimal to float for JSON serialization
                formatted[key] = float(value)
            else:
                formatted[key] = value
        return formatted
    return data


@app.route('/')
def index():
    """Render main page."""
    return render_template('index.html')


@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current database configuration."""
    config = conn_manager.config.copy()
    # Hide password
    config['password'] = '******' if config.get('password') else ''
    return jsonify(config)


@app.route('/api/config', methods=['POST'])
def update_config():
    """Update database configuration."""
    try:
        data = request.json
        conn_manager.update_config(**data)
        return jsonify({'success': True, 'message': 'Configuration saved'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/test-connection', methods=['POST'])
def test_connection():
    """Test database connection."""
    try:
        data = request.json
        # Create temporary connection manager with test config
        test_conn = ConnectionManager()
        test_conn.config = {**test_conn.config, **data}
        if test_conn.test_connection():
            return jsonify({'success': True, 'message': 'Connection successful!'})
        else:
            return jsonify({'success': False, 'message': 'Connection failed'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/query/instance-info', methods=['POST'])
def query_instance_info():
    """Query instance information."""
    try:
        data = request.json
        prod_inst_id = data.get('prod_inst_id', '').strip()
        if not prod_inst_id:
            return jsonify({'success': False, 'message': 'PROD_INST_ID is required'})

        results, sql = query_manager.get_instance_info(prod_inst_id)
        return jsonify({
            'success': True,
            'data': format_datetime_result(results),
            'sql': sql,
            'count': len(results)
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/query/change-log', methods=['POST'])
def query_change_log():
    """Query change log."""
    try:
        data = request.json
        prod_inst_id = data.get('prod_inst_id', '').strip()
        if not prod_inst_id:
            return jsonify({'success': False, 'message': 'PROD_INST_ID is required'})

        results, sql = query_manager.get_change_log(prod_inst_id)
        return jsonify({
            'success': True,
            'data': format_datetime_result(results),
            'sql': sql,
            'count': len(results)
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/query/change-record', methods=['POST'])
def query_change_record():
    """Query change record."""
    try:
        data = request.json
        prod_inst_id = data.get('prod_inst_id', '').strip()
        if not prod_inst_id:
            return jsonify({'success': False, 'message': 'PROD_INST_ID is required'})

        results, sql = query_manager.get_change_record(prod_inst_id)
        return jsonify({
            'success': True,
            'data': format_datetime_result(results),
            'sql': sql,
            'count': len(results)
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/query/all', methods=['POST'])
def query_all():
    """Execute all queries."""
    try:
        data = request.json
        prod_inst_id = data.get('prod_inst_id', '').strip()
        if not prod_inst_id:
            return jsonify({'success': False, 'message': 'PROD_INST_ID is required'})

        results = query_manager.get_all_queries(prod_inst_id)

        # Validate change record data
        validation_result = query_manager.validate_change_record(results['change_record'])

        return jsonify({
            'success': True,
            'data': {
                'instance_info': format_datetime_result(results['instance_info']),
                'change_log': format_datetime_result(results['change_log']),
                'change_record': format_datetime_result(results['change_record'])
            },
            'sql': results['sql'],
            'counts': {
                'instance_info': len(results['instance_info']),
                'change_log': len(results['change_log']),
                'change_record': len(results['change_record'])
            },
            'validation': validation_result
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/generate-llm-sql', methods=['POST'])
def generate_llm_sql():
    """Generate SQL fix using LLM (supports Zhipu AI GLM and Qwen)."""
    try:
        data = request.json
        current_data = data.get('currentData', [])
        violation_info = data.get('violationInfo', '')
        log_data = data.get('logData', [])  # Accept log data
        debug = data.get('debug', True)  # Debug mode flag
        model = data.get('model', os.getenv('LLM_MODEL', 'glm-4-flash'))
        provider = data.get('provider', os.getenv('LLM_PROVIDER', 'auto'))

        if not current_data:
            return jsonify({'success': False, 'message': 'Current data is required'})

        # Import here to avoid startup failures if API key not configured
        try:
            from src.llm.sql_generator import SQLGeneratorAgent
        except ImportError:
            return jsonify({
                'success': False,
                'message': 'LLM module not available. Please install dependencies.'
            })

        # Create LLM agent and generate SQL
        llm_agent = SQLGeneratorAgent(model=model, debug=debug, provider=provider)
        result = llm_agent.generate_fix_sql(current_data, violation_info, log_data)

        response_data = {
            'success': True,
            'sql': result['sql'],
            'explanation': result.get('explanation', ''),
            'model': model,
            'provider': llm_agent.provider
        }

        # Include debug information if debug mode is enabled
        if debug and hasattr(llm_agent, 'last_prompt') and llm_agent.last_prompt:
            response_data['debug'] = {
                'dataRowCount': len(current_data),
                'logRowCount': len(log_data) if log_data else 0,
                'prompt': llm_agent.last_prompt
            }

        return jsonify(response_data)
    except ValueError as e:
        # Handle missing API key
        return jsonify({
            'success': False,
            'message': str(e)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'LLM generation failed: {str(e)}'
        })


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
