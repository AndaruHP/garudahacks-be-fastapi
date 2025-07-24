import os
import google.generativeai as genai
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-flash')

app = FastAPI()

allowed_origins = os.getenv(
    "ALLOWED_ORIGINS", "http://localhost,http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in allowed_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LessonRequest(BaseModel):
    topic: str
    grade_level: str
    language: str


@app.post("/generate-lesson")
async def generate_lesson_endpoint(request: LessonRequest):
    """
    Endpoint ini menerima topik, jenjang kelas, dan bahasa,
    lalu menghasilkan paket pelajaran menggunakan AI.
    """
    print(f"Menerima permintaan untuk topik: {request.topic}")

    prompt = f"""
    Anda adalah asisten guru yang ahli untuk kelas {request.grade_level} di Indonesia.
    Buatkan sebuah paket pelajaran lengkap dalam bahasa {request.language} tentang "{request.topic}".

    Paket pelajaran harus berisi tiga bagian yang jelas:
    1.  Rencana Pelajaran Sederhana: Langkah-langkah singkat untuk guru.
    2.  Materi Bacaan untuk Siswa: Cerita atau penjelasan yang mudah dipahami dan relevan dengan budaya Indonesia.
    3.  Latihan Soal: 5 pertanyaan (campuran pilihan ganda dan isian singkat) berdasarkan materi bacaan, beserta kunci jawaban.

    Format output harus jelas dan terstruktur dengan baik.
    """

    response = model.generate_content(prompt)

    return {"lesson_packet": response.text}


@app.get("/")
def read_root():
    return {"message": "Server Proyek Pelita berjalan! Gunakan endpoint /generate-lesson untuk membuat pelajaran."
            }
