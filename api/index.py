from flask import Flask, request, jsonify, send_file
from werkzeug.utils import secure_filename
import os
import sys
import tempfile
from pathlib import Path

# Add parent to path so we can import convert_mathtype_to_latex
sys.path.insert(0, str(Path(__file__).parent.parent))

from convert_mathtype_to_latex import process_docx

app = Flask(__name__)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def allowed_file(filename):
    return filename.lower().endswith('.docx')

@app.route('/')
@app.route('/api')
@app.route('/api/')
def api_root():
    return jsonify({
        'status': 'ok',
        'service': 'MathType to LaTeX Converter',
        'version': '1.0'
    })

@app.route('/api/convert', methods=['POST'])
def convert():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']

    if not file or file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Only .docx files supported'}), 400

    # Check size
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)

    if size > MAX_FILE_SIZE:
        return jsonify({'error': 'File too large (max 10MB)'}), 413

    input_path = None
    output_path = None

    try:
        # Use /tmp for Vercel serverless
        tmp_dir = tempfile.gettempdir()
        input_path = os.path.join(tmp_dir, f'input_{os.getpid()}.docx')
        output_path = os.path.join(tmp_dir, f'output_{os.getpid()}.docx')

        file.save(input_path)
        process_docx(input_path, output_path)

        base_name = Path(secure_filename(file.filename)).stem
        return send_file(
            output_path,
            as_attachment=True,
            download_name=f'{base_name}-latex.docx',
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        for path in [input_path, output_path]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except:
                    pass

# Vercel requires the Flask app to be exposed as 'app' at module level
# The @vercel/python builder will handle WSGI automatically
