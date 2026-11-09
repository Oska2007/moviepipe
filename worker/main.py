import os
import subprocess
import boto3
import asyncio
from faster_whisper import WhisperModel
from deep_translator import GoogleTranslator
from telegram import Bot
from celery import Celery
import logging

# Logging සැකසුම
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Celery (Queue එක සඳහා)
app = Celery('tasks', broker='redis://redis:6379/0')

# Cloudflare R2 සැකසුම
s3_client = boto3.client(
    's3',
    endpoint_url=os.getenv('R2_ENDPOINT_URL'), # https://<ACCOUNT_ID>.r2.cloudflarestorage.com
    aws_access_key_id=os.getenv('R2_ACCESS_KEY'),
    aws_secret_access_key=os.getenv('R2_SECRET_KEY')
)
R2_BUCKET = os.getenv('R2_BUCKET')

# Telegram Bot සැකසුම
bot_token = os.getenv('TELEGRAM_TOKEN')
chat_id = os.getenv('TELEGRAM_CHAT_ID')

# R2 Upload Progress Callback
class ProgressPercentage(object):
    def __init__(self, filename, message_id):
        self._filename = filename
        self._size = float(os.path.getsize(filename))
        self._seen_so_far = 0
        self._message_id = message_id

    def __call__(self, bytes_amount):
        self._seen_so_far += bytes_amount
        percentage = (self._seen_so_far / self._size) * 100
        # සෑම 10% කට වරක් ප්‍රගතිය update කරයි
        if int(percentage) % 10 == 0:
            logger.info(f"Uploading to R2: {percentage:.2f}%")
            # මෙතනින් Telegram එකට ප්‍රගතිය යැවිය හැක (අවශ්‍ය නම්)

@app.task
def process_video(file_path):
    try:
        logger.info(f"Starting processing for: {file_path}")
        
        # 1. උපසිරැසි සෑදීම (Faster-Whisper)
        model = WhisperModel("base", device="cpu", compute_type="int8")
        segments, info = model.transcribe(file_path, beam_size=5)
        
        english_srt = file_path.rsplit('.', 1)[0] + "_en.srt"
        sinhala_srt = file_path.rsplit('.', 1)[0] + "_si.srt"
        
        with open(english_srt, "w", encoding="utf-8") as f:
            for i, segment in enumerate(segments, start=1):
                # මෙතනදී SRT format එකට ලියවෙනවා
                start_time = f"{int(segment.start//3600):02d}:{int((segment.start%3600)//60):02d}:{int(segment.start%60):02d},{int((segment.start%1)*1000):03d}"
                end_time = f"{int(segment.end//3600):02d}:{int((segment.end%3600)//60):02d}:{int(segment.end%60):02d},{int((segment.end%1)*1000):03d}"
                f.write(f"{i}\n{start_time} --> {end_time}\n{segment.text.strip()}\n\n")
        
        # 2. සිංහලට පරිවර්තනය කිරීම
        logger.info("Translating to Sinhala...")
        translator = GoogleTranslator(source='en', target='si')
        with open(english_srt, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        with open(sinhala_srt, "w", encoding="utf-8") as f:
            for line in lines:
                if "-->" in line or line.strip().isdigit() or not line.strip():
                    f.write(line) # ටයිම් සහ අංක එහෙම්මම තියන්න
                else:
                    try:
                        translated = translator.translate(line.strip())
                        f.write(translated + "\n")
                    except:
                        f.write(line) # එරර් එකක් ආවොත් ඉංග්‍රීසිම තියන්න

        # 3. x264 MP4 බවට පත් කිරීම (Soft Subs සමඟ)
        logger.info("Converting to x264 MP4 with soft subtitles...")
        output_mp4 = file_path.rsplit('.', 1)[0] + "_x264.mp4"
        
        # මෙතනදී ඉංග්‍රීසි සහ සිංහල උපසිරැසි දෙකම වීඩියෝ එකට embed කරනවා (Soft subs)
        ffmpeg_cmd = [
            'ffmpeg', '-y', '-i', file_path,
            '-i', english_srt, '-i', sinhala_srt,
            '-map', '0:v', '-map', '0:a', '-map', '1:s', '-map', '2:s',
            '-c:v', 'libx264', '-crf', '23', '-preset', 'fast',
            '-c:a', 'aac',
            '-c:s', 'mov_text',
            '-metadata:s:s:0', 'language=eng',
            '-metadata:s:s:0', 'title=English',
            '-metadata:s:s:1', 'language=sin',
            '-metadata:s:s:1', 'title=Sinhala',
            output_mp4
        ]
        subprocess.run(ffmpeg_cmd, check=True)

        # 4. R2 වෙත උඩුගත කිරීම (ප්‍රගතිය සමඟ)
        logger.info("Uploading to R2...")
        file_name = os.path.basename(output_mp4)
        
        # අපි Telegram එකට ප්‍රගතිය යැවීමට අලුත් Bot එකක් හදමු
        async def send_progress(msg):
            bot = Bot(token=bot_token)
            await bot.send_message(chat_id=chat_id, text=msg)
            
        # Upload කිරීම (මෙතනදී progress callback එක පාවිච්චි කරන්න පුළුවන්)
        s3_client.upload_file(
            output_mp4, R2_BUCKET, file_name,
            Callback=ProgressPercentage(output_mp4, None)
        )
        
        # 5. Telegram වෙත යැවීම
        logger.info("Uploading to Telegram...")
        async def send_to_telegram():
            bot = Bot(token=bot_token)
            with open(output_mp4, 'rb') as f:
                await bot.send_video(
                    chat_id=chat_id, 
                    video=f, 
                    caption=f"🎬 Processed: {file_name}\n✅ Subtitles: English & Sinhala"
                )
        asyncio.run(send_to_telegram())

        # 6. පිරිසිදු කිරීම (Storage Clear කිරීම)
        logger.info("Cleaning up files...")
        os.remove(file_path)
        os.remove(output_mp4)
        os.remove(english_srt)
        os.remove(sinhala_srt)
        logger.info(f"Successfully processed and cleaned up: {file_name}")

    except Exception as e:
        logger.error(f"Error processing {file_path}: {str(e)}")