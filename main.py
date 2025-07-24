import os
import google.generativeai as genai
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel

# --- Bagian Setup AI (Sama seperti sebelumnya) ---
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-flash')
# ------------------------------------------------

# Inisialisasi aplikasi FastAPI
app = FastAPI()

# Definisikan struktur data untuk permintaan yang masuk
class LessonRequest(BaseModel):
    topic: str
    grade_level: str
    language: str

# Buat endpoint API
@app.post("/generate-lesson")
async def generate_lesson_endpoint(request: LessonRequest):
    """
    Endpoint ini menerima topik, jenjang kelas, dan bahasa,
    lalu menghasilkan paket pelajaran menggunakan AI.
    """
    print(f"Menerima permintaan untuk topik: {request.topic}")

    # Ini adalah "Prompt Engineering" di mana kita membuat instruksi detail untuk AI
    prompt = f"""
    Anda adalah asisten guru yang ahli untuk kelas {request.grade_level} di Indonesia.
    Buatkan sebuah paket pelajaran lengkap dalam bahasa {request.language} tentang "{request.topic}".

    Paket pelajaran harus berisi tiga bagian yang jelas:
    1.  Rencana Pelajaran Sederhana: Langkah-langkah singkat untuk guru.
    2.  Materi Bacaan untuk Siswa: Cerita atau penjelasan yang mudah dipahami dan relevan dengan budaya Indonesia.
    3.  Latihan Soal: 5 pertanyaan (campuran pilihan ganda dan isian singkat) berdasarkan materi bacaan, beserta kunci jawaban.

    Format output harus jelas dan terstruktur dengan baik.
    """

    # Kirim prompt ke AI
    response = model.generate_content(prompt)

    # Kembalikan teks yang dihasilkan oleh AI dalam format JSON
    return {"lesson_packet": response.text}

@app.get("/")
def read_root():
    return {"message": "Server Proyek Pelita berjalan! Gunakan endpoint /generate-lesson untuk membuat pelajaran."}