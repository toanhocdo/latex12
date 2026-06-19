"""
Vercel Serverless Function: MathType to LaTeX Converter
"""

import os
import sys
import tempfile
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from flask import Flask, request, jsonify, send_file
    from werkzeug.utils import secure_filename
    from convert_mathtype_to_latex import process_docx
except ImportError as e:
    print(f"Import error: {e}")
    raise

app = Flask(__name__)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {'.docx'}

def allowed_file(filename):
    """Check if file extension is allowed."""
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET'])
@app.route('/api', methods=['GET'])
@app.route('/api/', methods=['GET'])
def index():
    """Health check endpoint."""
    return jsonify({
        'status': 'ok',
        'service': 'MathType to LaTeX Converter',
        'endpoints': {
            'convert': 'POST /api/convert',
            'health': 'GET /api/health'
        }
    })

@app.route('/health', methods=['GET'])
@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok', 'service': 'MathType to LaTeX'})

@app.route('/convert', methods=['POST'])
@app.route('/api/convert', methods=['POST'])
def convert():
    """Convert MathType to LaTeX in uploaded .docx file."""

    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not allowed_file(file.filename):
            return jsonify({'error': 'Only .docx files are supported'}), 400

        # Check file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)

        if file_size > MAX_FILE_SIZE:
            return jsonify({'error': f'File too large. Max: {MAX_FILE_SIZE/(1024*1024):.1f}MB'}), 413

        input_path = None
        output_path = None

        try:
            # Create temp files in /tmp (only writable dir in Vercel)
            input_fd, input_path = tempfile.mkstemp(suffix='.docx', dir='/tmp')
            os.close(input_fd)

            output_fd, output_path = tempfile.mkstemp(suffix='.docx', dir='/tmp')
            os.close(output_fd)

            # Save uploaded file
            file.save(input_path)

            # Convert
            process_docx(input_path, output_path)

            # Generate output filename
            original_name = secure_filename(file.filename)
            base_name = Path(original_name).stem
            output_filename = f"{base_name}-latex.docx"

            # Return converted file
            return send_file(
                output_path,
                as_attachment=True,
                download_name=output_filename,
                mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )

        finally:
            # Cleanup temp files
            try:
                if input_path and os.path.exists(input_path):
                    os.remove(input_path)
                if output_path and os.path.exists(output_path):
                    os.remove(output_path)
            except Exception as cleanup_error:
                print(f"Cleanup error: {cleanup_error}")

    except Exception as e:
        print(f"Conversion error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Conversion failed: {str(e)}'}), 500

# WSGI application for Vercel
application = app

# For local testing
if __name__ == '__main__':
    app.run(debug=True)
