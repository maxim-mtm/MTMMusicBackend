import os
import tempfile
from flask import Flask, request, jsonify
from yt_dlp import YoutubeDL

app = Flask(__name__)

# Optional: limit max file size (for safety on Render)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB

def write_cookies_to_tempfile():
    cookies_content = os.getenv('COOKIES_TXT_VAR')
    if not cookies_content:
        raise Exception("Missing COOKIES_TXT_VAR environment variable")

    temp = tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.txt')
    temp.write(cookies_content)
    temp.close()
    return temp.name

def download_audio_from_youtube(url, output_path):
    cookies_file = write_cookies_to_tempfile()

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_path,
        'cookiefile': cookies_file,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'noplaylist': True
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return output_path, info.get('title', 'Unknown Title')

@app.route('/')
def home():
    return 'Server is running.'

@app.route('/download', methods=['POST'])
def download():
    data = request.get_json()
    url = data.get('url')

    if not url:
        return jsonify({'error': 'Missing URL'}), 400

    try:
        output_file = tempfile.mktemp(suffix='.mp3')
        file_path, title = download_audio_from_youtube(url, output_file)
        return jsonify({'success': True, 'file': file_path, 'title': title})
    except Exception as e:
        return jsonify({'error': f'Failed to download audio: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True)
