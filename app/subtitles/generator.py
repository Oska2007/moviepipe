import os
import logging
from faster_whisper import WhisperModel
from deep_translator import GoogleTranslator

logger = logging.getLogger(__name__)

def format_timestamp(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"

def generate_subtitles(video_path: str, output_dir: str) -> tuple[str, str]:
    model_size = os.getenv("WHISPER_MODEL", "small")
    compute_type = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
    
    logger.info(f"Loading Whisper model: {model_size} (Compute: {compute_type})...")
    
    model = WhisperModel(
        model_size, 
        device="cpu", 
        compute_type=compute_type,
        cpu_threads=2 
    )
    
    logger.info("Transcribing audio...")
    segments, info = model.transcribe(
        video_path, 
        beam_size=5, 
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500)
    )
    
    logger.info(f"Detected language: {info.language}")
    
    eng_srt_path = os.path.join(output_dir, "english.srt")
    sin_srt_path = os.path.join(output_dir, "sinhala.srt")
    
    translator = GoogleTranslator(source='auto', target='si')
    
    with open(eng_srt_path, "w", encoding="utf-8") as eng_file, \
         open(sin_srt_path, "w", encoding="utf-8") as sin_file:
        
        for i, segment in enumerate(segments, start=1):
            start_time = format_timestamp(segment.start)
            end_time = format_timestamp(segment.end)
            eng_text = segment.text.strip()
            
            if not eng_text:
                continue
                
            eng_file.write(f"{i}\n{start_time} --> {end_time}\n{eng_text}\n\n")
            
            try:
                sin_text = translator.translate(eng_text)
                if not sin_text:
                    sin_text = eng_text
            except Exception as e:
                logger.error(f"Translation failed: {e}")
                sin_text = f"[Translation Failed] {eng_text}"
                
            sin_file.write(f"{i}\n{start_time} --> {end_time}\n{sin_text}\n\n")
            
    return eng_srt_path, sin_srt_path