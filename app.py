import os
import tempfile
import requests
from flask import Flask, request, send_file, jsonify
import yt_dlp
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC

app = Flask(__name__)

DEEZER_SEARCH_URL = "https://api.deezer.com/search?q="

def fetch_deezer_metadata(track_title):
    query = f"{track_title} lyrics"
    response = requests.get(DEEZER_SEARCH_URL + query)
    if response.status_code == 200:
        data = response.json()
        if data['data']:
            track = data['data'][0]
            artist = track['artist']['name']
            album = track['album']['title']
            cover_url = track['album']['cover_big']
            return artist, album, cover_url
    return None, None, None

def download_audio_from_youtube(url, download_path):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': download_path,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'no_warnings': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        filename = os.path.splitext(filename)[0] + ".mp3"
        return filename, info.get('title', None)

def embed_metadata(mp3_path, artist, album, cover_url, title):
    audio = EasyID3(mp3_path)
    audio['artist'] = artist or ""
    audio['album'] = album or ""
    audio['title'] = title or ""
    audio.save()

    if cover_url:
        img_data = requests.get(cover_url).content
        audio = MP3(mp3_path, ID3=ID3)
        if audio.tags is None:
            audio.add_tags()
        audio.tags.add(
            APIC(
                encoding=3,
                mime='image/jpeg',
                type=3,
                desc='Cover',
                data=img_data
            )
        )
        audio.save()

@app.route('/download', methods=['POST'])
def download():
    data = request.json
    url = data.get('url')
    if not url:
        return jsonify({"error": "Missing 'url' parameter"}), 400

    with tempfile.TemporaryDirectory() as tmpdirname:
        download_path = os.path.join(tmpdirname, '%(title)s.%(ext)s')
        try:
            mp3_file, video_title = download_audio_from_youtube(url, download_path)
        except Exception as e:
            return jsonify({"error": f"Failed to download audio: {str(e)}"}), 500

        artist, album, cover_url = fetch_deezer_metadata(video_title or "")

        try:
            embed_metadata(mp3_file, artist, album, cover_url, video_title)
        except Exception as e:
            print("Metadata embedding failed:", e)

        return send_file(mp3_file, mimetype='audio/mpeg', as_attachment=True,
                         download_name=f"{video_title or 'audio'}.mp3")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')