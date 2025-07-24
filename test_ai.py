import os
import google.generativeai as genai
from dotenv import load_dotenv

# Muat environment variable dari file .env
load_dotenv()

# Konfigurasi AI dengan kunci API Anda
api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)

# Inisialisasi model AI
# Kita menggunakan 'gemini-1.5-flash', yang cepat dan efisien, cocok untuk hackathon
model = genai.GenerativeModel('gemini-1.5-flash')

# Buat prompt (pertanyaan) untuk AI
prompt = "Sebutkan 3 fakta menarik tentang kota Tangerang Selatan dalam Bahasa Indonesia."

print("Mengirim permintaan ke AI...")

# Kirim prompt ke model AI dan dapatkan responsnya
response = model.generate_content(prompt)

print("--- Jawaban dari AI ---")
print(response.text)
print("-----------------------")