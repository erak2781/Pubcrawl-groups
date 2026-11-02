from flask import Flask, request, jsonify
from flask_cors import CORS
import openrouteservice
from .create_group import create_groups
from .generate_path import (
    calculate_shortest_path,
    uppsala_nations_coordinates,
    get_ors_walking_distances,
)

app = Flask(__name__)
CORS(app)

@app.route('/api/generate-groups', methods=['POST'])
def generate_groups():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    num_groups = request.form.get('num_groups', type=int)

    if not num_groups or num_groups < 1:
        return jsonify({'error': 'Invalid number of groups'}), 400

    try:
        name_col = request.form.get('name_col', type=int)
        partner_col = request.form.get('partner_col', type=int)  # None if empty
        has_header = request.form.get('has_header', 'true') == 'true'
        delimiter = request.form.get('delimiter', ',')

        if name_col is None or name_col < 0:
            return jsonify({'error': 'Invalid name column'}), 400
        if name_col == partner_col:
            return jsonify({'error': 'Name and partner must be different columns'}), 400

        csv_text = file.read().decode('utf-8-sig')
        groups = create_groups(num_groups, csv_text, name_col, partner_col, has_header, delimiter)
        return jsonify({'groups': groups})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-path', methods=['POST'])
def generate_path():
    data = request.get_json(silent=True) or {}
    if not data or 'pubs' not in data:
        return jsonify({'error': 'missing pubs in list'}), 400

    pubs = data.get('pubs')
    if not isinstance(pubs, list) or len(pubs) < 2:
        return jsonify({'error': 'need more than 1 pub'}), 400
    invalid_pubs = [p for p in pubs if p not in uppsala_nations_coordinates]
    if invalid_pubs:
        return jsonify({'error': f'Cant find pubs {invalid_pubs}'}), 400
    start = data.get('start', pubs[0])
    if start not in pubs:
        return jsonify({'error': f'Start pub {start}, must be in pub list'}), 400
    try:
        dist_dict, index_translate = get_ors_walking_distances(pubs)


        paths = calculate_shortest_path(dist_dict, index_translate, start)

        return jsonify({
            'start' : start,
            'paths' : paths,
            'total_stops' : len(paths[0])
        }), 200
    except openrouteservice.exceptions.ApiError as e:
        return jsonify({'error': f'OpenRouteService API error: {str(e)}'}), 502
    except Exception as e:
        return jsonify({'error': str(e)}), 500