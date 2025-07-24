import os
import google.generativeai as genai
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import re
import json
from typing import Optional, List, Dict

# --- Bagian Setup AI ---
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-flash')

# ------------------------------------------------
# Inisialisasi aplikasi FastAPI
app = FastAPI()

# Model untuk pertanyaan individual
class Question(BaseModel):
    number: int
    type: str  # "multiple_choice" atau "short_answer"
    question: str
    options: Optional[List[str]] = None  # Hanya untuk multiple choice

# Model untuk jawaban individual
class Answer(BaseModel):
    number: int
    answer: str
    explanation: Optional[str] = None

# Definisikan struktur data untuk permintaan yang masuk
class LessonRequest(BaseModel):
    topic: str = Field(..., description="Topic of the lesson", min_length=1)
    grade_level: str = Field(..., description="Grade level (e.g., '4th grade', 'grade 4')", min_length=1)
    language: str = Field(..., description="Language for the lesson", min_length=1)
    
    class Config:
        schema_extra = {
            "example": {
                "topic": "Rain",
                "grade_level": "4th grade",
                "language": "English"
            }
        }

# Definisikan struktur data untuk response dengan array
class LessonResponse(BaseModel):
    rencana_belajar: str
    materi_belajar: str
    latihan_soal: List[Question]  # Array of questions
    kunci_jawaban: List[Answer]   # Array of answers
    
    class Config:
        schema_extra = {
            "example": {
                "rencana_belajar": "1. Introduction to topic\n2. Main explanation\n3. Interactive discussion",
                "materi_belajar": "Reading material for students...",
                "latihan_soal": [
                    {
                        "number": 1,
                        "type": "multiple_choice",
                        "question": "What is rain?",
                        "options": ["A) Water from sky", "B) Snow", "C) Wind", "D) Fire"]
                    },
                    {
                        "number": 2,
                        "type": "short_answer",
                        "question": "Name three benefits of rain.",
                        "options": None
                    }
                ],
                "kunci_jawaban": [
                    {
                        "number": 1,
                        "answer": "A",
                        "explanation": "Rain is water falling from the sky"
                    },
                    {
                        "number": 2,
                        "answer": "Water plants, fill reservoirs, clean air",
                        "explanation": "Rain provides water for plants and other uses"
                    }
                ]
            }
        }

def parse_questions_and_answers(exercises_text: str, answers_text: str) -> tuple:
    """
    Parse latihan soal dan kunci jawaban menjadi array terstruktur
    """
    questions = []
    answers = []
    
    # Parse questions
    if exercises_text:
        # Split berdasarkan nomor soal
        question_parts = re.split(r'\n?\d+\.\s*', exercises_text)
        question_parts = [part.strip() for part in question_parts if part.strip()]
        
        for i, part in enumerate(question_parts, 1):
            # Cek apakah ini multiple choice (mengandung A), B), C), D))
            if re.search(r'[A-D]\)', part):
                # Multiple choice
                lines = part.split('\n')
                question_text = lines[0].strip()
                options = []
                
                for line in lines[1:]:
                    if re.match(r'^[A-D]\)', line.strip()):
                        options.append(line.strip())
                
                questions.append(Question(
                    number=i,
                    type="multiple_choice",
                    question=question_text,
                    options=options if options else None
                ))
            else:
                # Short answer
                questions.append(Question(
                    number=i,
                    type="short_answer",
                    question=part.strip(),
                    options=None
                ))
    
    # Parse answers
    if answers_text:
        # Split berdasarkan nomor jawaban
        answer_parts = re.split(r'\n?\d+\.\s*', answers_text)
        answer_parts = [part.strip() for part in answer_parts if part.strip()]
        
        for i, part in enumerate(answer_parts, 1):
            # Pisahkan jawaban dan penjelasan
            if ' - ' in part:
                answer_text, explanation = part.split(' - ', 1)
            elif ': ' in part:
                answer_text, explanation = part.split(': ', 1)
            else:
                answer_text = part
                explanation = None
            
            answers.append(Answer(
                number=i,
                answer=answer_text.strip(),
                explanation=explanation.strip() if explanation else None
            ))
    
    return questions, answers

def parse_lesson_content(content: str) -> dict:
    """
    Parse konten pelajaran dari AI menjadi struktur JSON yang terorganisir
    """
    result = {
        "rencana_belajar": "",
        "materi_belajar": "",
        "latihan_soal": [],
        "kunci_jawaban": []
    }
    
    # Pola regex untuk menangkap setiap bagian
    patterns = {
        "rencana_belajar": r"(?:Rencana Pelajaran Sederhana|Lesson Plan|1\.\s*Rencana Pelajaran|1\.\s*Lesson Plan)[:\s]*\n(.*?)(?=(?:Materi Bacaan|Reading Material|2\.\s*Materi Bacaan|2\.\s*Reading Material|Latihan Soal|Exercises|$))",
        "materi_belajar": r"(?:Materi Bacaan untuk Siswa|Reading Material|2\.\s*Materi Bacaan|2\.\s*Reading Material)[:\s]*\n(.*?)(?=(?:Latihan Soal|Exercises|3\.\s*Latihan Soal|3\.\s*Exercises|Kunci Jawaban|Answer Key|$))",
        "latihan_soal": r"(?:Latihan Soal|Exercises|3\.\s*Latihan Soal|3\.\s*Exercises)[:\s]*\n(.*?)(?=(?:Kunci Jawaban|Answer Key|Jawaban|Answers|$))",
        "kunci_jawaban": r"(?:Kunci Jawaban|Answer Key|Jawaban|Answers)[:\s]*\n(.*?)$"
    }
    
    exercises_text = ""
    answers_text = ""
    
    for key, pattern in patterns.items():
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            if key in ["rencana_belajar", "materi_belajar"]:
                result[key] = match.group(1).strip()
            elif key == "latihan_soal":
                exercises_text = match.group(1).strip()
            elif key == "kunci_jawaban":
                answers_text = match.group(1).strip()
    
    # Parse questions and answers into arrays
    if exercises_text or answers_text:
        questions, answers = parse_questions_and_answers(exercises_text, answers_text)
        result["latihan_soal"] = questions
        result["kunci_jawaban"] = answers
    
    # Jika parsing gagal, coba metode fallback
    if not result["rencana_belajar"] and not result["materi_belajar"]:
        lines = content.split('\n')
        current_section = None
        current_content = []
        
        for line in lines:
            line = line.strip()
            if re.search(r'rencana pelajaran|lesson plan', line, re.IGNORECASE):
                if current_section and current_content:
                    if current_section == 'latihan_soal':
                        exercises_text = '\n'.join(current_content).strip()
                    elif current_section == 'kunci_jawaban':
                        answers_text = '\n'.join(current_content).strip()
                    else:
                        result[current_section] = '\n'.join(current_content).strip()
                current_section = 'rencana_belajar'
                current_content = []
            elif re.search(r'materi bacaan|reading material', line, re.IGNORECASE):
                if current_section and current_content:
                    if current_section == 'latihan_soal':
                        exercises_text = '\n'.join(current_content).strip()
                    elif current_section == 'kunci_jawaban':
                        answers_text = '\n'.join(current_content).strip()
                    else:
                        result[current_section] = '\n'.join(current_content).strip()
                current_section = 'materi_belajar'
                current_content = []
            elif re.search(r'latihan soal|exercises', line, re.IGNORECASE):
                if current_section and current_content:
                    if current_section == 'kunci_jawaban':
                        answers_text = '\n'.join(current_content).strip()
                    else:
                        result[current_section] = '\n'.join(current_content).strip()
                current_section = 'latihan_soal'
                current_content = []
            elif re.search(r'kunci jawaban|answer key|jawaban|answers', line, re.IGNORECASE):
                if current_section and current_content:
                    if current_section == 'latihan_soal':
                        exercises_text = '\n'.join(current_content).strip()
                    else:
                        result[current_section] = '\n'.join(current_content).strip()
                current_section = 'kunci_jawaban'
                current_content = []
            elif line and current_section:
                current_content.append(line)
        
        # Tambahkan konten terakhir
        if current_section and current_content:
            if current_section == 'latihan_soal':
                exercises_text = '\n'.join(current_content).strip()
            elif current_section == 'kunci_jawaban':
                answers_text = '\n'.join(current_content).strip()
            else:
                result[current_section] = '\n'.join(current_content).strip()
        
        # Parse questions and answers
        if exercises_text or answers_text:
            questions, answers = parse_questions_and_answers(exercises_text, answers_text)
            result["latihan_soal"] = questions
            result["kunci_jawaban"] = answers
    
    return result

# Buat endpoint API
@app.post("/generate-lesson", response_model=LessonResponse)
async def generate_lesson_endpoint(request: LessonRequest):
    """
    Endpoint ini menerima topik, jenjang kelas, dan bahasa,
    lalu menghasilkan paket pelajaran menggunakan AI dalam format JSON terstruktur dengan array.
    """
    try:
        print(f"Menerima permintaan untuk topik: {request.topic}")
        print(f"Grade level: {request.grade_level}")
        print(f"Language: {request.language}")
        
        # Validasi API key
        if not api_key:
            raise HTTPException(status_code=500, detail="Google API key not configured")
        
        # Prompt engineering yang disesuaikan dengan bahasa
        if request.language.lower() == "english":
            prompt = f"""
            You are an expert teaching assistant for {request.grade_level} students in Indonesia.
            Create a complete lesson package in {request.language} about "{request.topic}".
            
            IMPORTANT: Format the output EXACTLY like this with clear labels:

            Lesson Plan:
            1. [Step 1]
            2. [Step 2]  
            3. [Step 3]
            4. [Step 4]
            5. [Step 5]

            Reading Material:
            [Write an easy-to-understand story or explanation relevant to Indonesian culture, at least 3 paragraphs]

            Exercises:
            1. [Multiple choice question]
               A) [Option A]
               B) [Option B] 
               C) [Option C]
               D) [Option D]
            2. [Short answer question]
            3. [Multiple choice question]
               A) [Option A]
               B) [Option B]
               C) [Option C] 
               D) [Option D]
            4. [Short answer question]
            5. [Multiple choice question]
               A) [Option A]
               B) [Option B]
               C) [Option C]
               D) [Option D]

            Answer Key:
            1. A - [Explanation]
            2. [Expected answer] - [Explanation]
            3. B - [Explanation]
            4. [Expected answer] - [Explanation]
            5. C - [Explanation]

            Make sure each section has clear labels and is separated.
            """
        else:
            prompt = f"""
            Anda adalah asisten guru yang ahli untuk kelas {request.grade_level} di Indonesia.
            Buatkan sebuah paket pelajaran lengkap dalam bahasa {request.language} tentang "{request.topic}".
            
            PENTING: Format output harus TEPAT seperti ini dengan label yang jelas:

            Rencana Pelajaran Sederhana:
            1. [Langkah 1]
            2. [Langkah 2]
            3. [Langkah 3] 
            4. [Langkah 4]
            5. [Langkah 5]

            Materi Bacaan untuk Siswa:
            [Tuliskan cerita atau penjelasan yang mudah dipahami dan relevan dengan budaya Indonesia, minimal 3 paragraf]

            Latihan Soal:
            1. [Soal pilihan ganda]
               A) [Pilihan A]
               B) [Pilihan B]
               C) [Pilihan C]
               D) [Pilihan D]
            2. [Soal isian singkat]
            3. [Soal pilihan ganda]
               A) [Pilihan A]
               B) [Pilihan B]
               C) [Pilihan C]
               D) [Pilihan D]
            4. [Soal isian singkat]
            5. [Soal pilihan ganda]
               A) [Pilihan A]
               B) [Pilihan B]
               C) [Pilihan C]
               D) [Pilihan D]

            Kunci Jawaban:
            1. A - [Penjelasan]
            2. [Jawaban yang diharapkan] - [Penjelasan]
            3. B - [Penjelasan]
            4. [Jawaban yang diharapkan] - [Penjelasan]
            5. C - [Penjelasan]

            Pastikan setiap bagian memiliki label yang jelas dan terpisah.
            """
        
        # Kirim prompt ke AI
        response = model.generate_content(prompt)
        
        if not response or not response.text:
            raise HTTPException(status_code=500, detail="Failed to generate content from AI")
        
        print(f"AI Response length: {len(response.text)}")
        
        # Parse konten menjadi struktur yang terorganisir
        parsed_content = parse_lesson_content(response.text)
        
        # Validasi bahwa setidaknya ada beberapa bagian terisi
        if not parsed_content["rencana_belajar"] and not parsed_content["materi_belajar"]:
            # Fallback jika parsing gagal
            parsed_content = {
                "rencana_belajar": response.text,
                "materi_belajar": "Please check the lesson plan section for complete content.",
                "latihan_soal": [
                    Question(number=1, type="short_answer", question="Failed to parse questions", options=None)
                ],
                "kunci_jawaban": [
                    Answer(number=1, answer="Failed to parse answers", explanation=None)
                ]
            }
        
        return LessonResponse(**parsed_content)
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error generating lesson: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/")
def read_root():
    return {"message": "Server Proyek Pelita berjalan! Gunakan endpoint /generate-lesson untuk membuat pelajaran."}

# Endpoint tambahan untuk testing format
@app.get("/test-format")
def test_format():
    """Endpoint untuk testing format response dengan array"""
    return LessonResponse(
        rencana_belajar="1. Pembukaan dan salam\n2. Review materi sebelumnya\n3. Pengenalan topik baru\n4. Diskusi interaktif\n5. Evaluasi dan penutup",
        materi_belajar="Contoh materi bacaan untuk siswa yang mudah dipahami...",
        latihan_soal=[
            Question(
                number=1,
                type="multiple_choice",
                question="Apa yang dimaksud dengan hujan?",
                options=["A) Air yang jatuh dari langit", "B) Angin kencang", "C) Cahaya matahari", "D) Awan putih"]
            ),
            Question(
                number=2,
                type="short_answer", 
                question="Sebutkan 3 manfaat hujan untuk kehidupan!",
                options=None
            )
        ],
        kunci_jawaban=[
            Answer(
                number=1,
                answer="A",
                explanation="Hujan adalah air yang jatuh dari langit akibat kondensasi uap air"
            ),
            Answer(
                number=2,
                answer="Menyirami tanaman, mengisi waduk, membersihkan udara",
                explanation="Hujan memberikan air untuk berbagai kebutuhan makhluk hidup"
            )
        ]
    )

# Endpoint untuk testing request validation
@app.post("/test-request")
async def test_request(request: LessonRequest):
    """Test endpoint to validate request format"""
    return {
        "message": "Request received successfully",
        "data": {
            "topic": request.topic,
            "grade_level": request.grade_level,
            "language": request.language
        }
    }