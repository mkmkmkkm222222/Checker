import os
import base64
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import requests 

# --- PENGATURAN ---
DAFTAR_SUPIR = [
    "AMIL", "ANWAR", "INO", "ISMAIL",
    "JONA", "SAMUEL", "SIDIK", "SOLIHIN", "GODLINE", "AWANG", "SAFRUDIN","SENTRA STABILIZER","CV.GRATIA","CAB MEDAN","CAB BALI","TAM SURABAYA","TAM PALEMBANG","TAM BANDUNG","TAM PEKANBARU","TAM SEMARANG"
]
ID_FOLDER_INDUK = "1N24o7wGAHb8VraIVOYEchTKRtm5alCfC" 

# --- PENGATURAN NOTIFIKASI TELEGRAM ---
TELEGRAM_BOT_TOKEN = "8121771510:AAGRjyyIguXiOrKDZMuD0pwiN8JBuobSAKc"
TELEGRAM_CHAT_ID = "8401956870"

# Inisialisasi Aplikasi Web
app = Flask(__name__)
app.config['SECRET_KEY'] = 'rahasia-banget-loh'

def otentikasi_google_drive():
    gauth = GoogleAuth()
    gauth.LoadCredentialsFile("mycreds.txt")
    if gauth.credentials is None or gauth.access_token_expired:
        gauth.CommandLineAuth()
    else:
        gauth.Authorize()
    gauth.SaveCredentialsFile("mycreds.txt")
    return GoogleDrive(gauth)

# --- FUNGSI NOTIFIKASI DIPERBARUI UNTUK FOTO & VIDEO ---
def kirim_notifikasi_telegram(nama_supir, jumlah_foto, jumlah_video):
    if not TELEGRAM_BOT_TOKEN or "GANTI_DENGAN" in TELEGRAM_BOT_TOKEN:
        print("Peringatan: Token & Chat ID Telegram belum diatur. Melewatkan notifikasi.")
        return

    try:
        pesan = (
            f"📦 *Laporan Dokumentasi Checker*\n\n"
            f"👤 *Supir:* {nama_supir}\n"
            f"🖼️ *Foto:* {jumlah_foto} file\n"
            f"📹 *Video:* {jumlah_video} file\n"
            f"⏰ *Waktu:* {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n"
            f"Dokumentasi telah berhasil diunggah ke Google Drive."
        )
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': pesan, 'parse_mode': 'Markdown'}
        
        print(f"Mengirim notifikasi Telegram ke Chat ID {TELEGRAM_CHAT_ID}...")
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            print("Notifikasi Telegram berhasil dikirim.")
        else:
            print(f"Gagal mengirim notifikasi Telegram. Status: {response.status_code}, Response: {response.json()}")
    except Exception as e:
        print(f"Terjadi error saat mengirim notifikasi Telegram: {e}")

def cari_atau_buat_folder(drive, nama_folder, id_folder_induk):
    parent_query = f"'{id_folder_induk}' in parents" if id_folder_induk else "'root' in parents"
    query = f"title='{nama_folder}' and mimeType='application/vnd.google-apps.folder' and trashed=false and {parent_query}"
    
    file_list = drive.ListFile({'q': query}).GetList()
    if file_list:
        return file_list[0]['id']
    else:
        folder_metadata = {
            'title': nama_folder, 
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [{'id': id_folder_induk}] if id_folder_induk else []
        }
        folder = drive.CreateFile(folder_metadata)
        folder.Upload()
        return folder['id']

@app.route('/')
def index():
    return render_template('index.html', supir_list=DAFTAR_SUPIR)

# --- FUNGSI UPLOAD DIPERBARUI UNTUK FOTO & VIDEO ---
@app.route('/upload', methods=['POST'])
def upload():
    data = request.get_json()
    nama_supir = data.get('driver')
    media_files = data.get('media') # Mengambil array media
    if not nama_supir or not media_files: 
        return jsonify({'status': 'error', 'message': 'Data tidak lengkap.'}), 400

    try:
        drive = otentikasi_google_drive()
        id_folder_supir = cari_atau_buat_folder(drive, nama_supir, ID_FOLDER_INDUK)
        
        jumlah_foto_sukses = 0
        jumlah_video_sukses = 0
        
        for i, media_item in enumerate(media_files):
            header, encoded = media_item['dataUrl'].split(",", 1)
            file_bytes = base64.b64decode(encoded)
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            
            file_type = media_item['type']
            extension = ""
            if file_type == 'photo':
                extension = "png"
                jumlah_foto_sukses += 1
            elif file_type == 'video':
                # --- PERUBAHAN DI SINI ---
                extension = "mp4" # Mengubah ekstensi menjadi mp4
                jumlah_video_sukses += 1

            nama_file = f"dokumentasi_{file_type}_{timestamp}_{i+1}.{extension}"
            
            with open(nama_file, "wb") as f: 
                f.write(file_bytes)
            
            file_drive = drive.CreateFile({'title': nama_file, 'parents': [{'id': id_folder_supir}]})
            file_drive.SetContentFile(nama_file)
            file_drive.Upload()
            
            file_drive = None
            os.remove(nama_file)
        
        if jumlah_foto_sukses > 0 or jumlah_video_sukses > 0:
            kirim_notifikasi_telegram(nama_supir, jumlah_foto_sukses, jumlah_video_sukses)
            
        return jsonify({'status': 'success', 'message': f'Berhasil mengunggah {jumlah_foto_sukses} foto dan {jumlah_video_sukses} video.'})

    except Exception as e:
        print(f"Error di fungsi upload: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    print("Untuk memulai, buka browser dan akses alamat: http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
