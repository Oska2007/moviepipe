import os, subprocess, boto3, whisper
from telegram import Bot
from celery import Celery

# Celery සැකසුම
app = Celery('tasks', broker='redis://redis:6379/0')

# R2 සැකසුම
s3 = boto3.client('s3',
    endpoint_url='https://<ACCOUNT_ID>.r2.cloudflarestorage.com',
    aws_access_key_id=os.getenv('R2_ACCESS_KEY'),
    aws_secret_access_key=os.getenv('R2_SECRET_KEY')
)

@app.task
def process_video(file_path):
    # 1. Whisper භාවිතයෙන් උපසිරැසි ජනනය (English)
    model = whisper.load_model("base")
    result = model.transcribe(file_path)
    srt_content = result['text'] # සරල උදාහරණයක් (සත්‍ය ලෙස SRT ආකෘතියට හැරවිය යුතුය)
    
    # 2. x264 MP4 බවට පත් කිරීම (FFmpeg)
    output_path = file_path.replace('.mkv', '_x264.mp4')
    subprocess.run(['ffmpeg', '-i', file_path, '-c:v', 'libx264', '-c:a', 'aac', output_path])
    
    # 3. Cloudflare R2 වෙත උඩුගත කිරීම (ප්‍රගතිය සමඟ)
    # මෙහිදී S3 multipart upload භාවිතා කර ප්‍රගතිය Telegram වෙත යවන්න
    s3.upload_file(output_path, os.getenv('R2_BUCKET'), os.path.basename(output_path))
    
    # 4. Telegram වෙත යැවීම
    bot = Bot(token=os.getenv('TELEGRAM_TOKEN'))
    bot.send_document(chat_id=os.getenv('TELEGRAM_CHAT_ID'), document=open(output_path, 'rb'))
    
    # 5. පිරිසිදු කිරීම
    os.remove(file_path)
    os.remove(output_path)

# (මෙය Django/FastAPI වැනි Web Framework එකක් සමඟ ඒකාබද්ධ කර, 
# Aria2 බාගැනීම අවසන් වූ පසු මෙම task එක ධාවනය කරන්න)