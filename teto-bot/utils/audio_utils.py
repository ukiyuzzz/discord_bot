"""
Вспомогательные функции для работы с аудио:
- pcm_to_wav: заворачивает сырой PCM (как отдаёт discord voice receive) в WAV
  с заголовком, который понимает Groq Whisper API.
- play_bytes_in_voice: проигрывает произвольные аудио-байты (например, mp3
  от Fish Audio) в голосовом канале через ffmpeg.
"""
import io
import os
import subprocess
import tempfile
import wave

import discord


def convert_to_wav_bytes(input_bytes: bytes) -> bytes:
    """
    Конвертирует произвольный аудио-формат (ogg/opus из голосовых сообщений
    Discord, mp3, m4a и т.д.) в WAV 16kHz mono — надёжный формат для STT.
    ffmpeg сам определяет формат по содержимому файла, поэтому явно его не указываем.
    """
    result = subprocess.run(
        ["ffmpeg", "-i", "pipe:0", "-f", "wav", "-ar", "16000", "-ac", "1", "pipe:1"],
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg не смог сконвертировать аудио: {result.stderr.decode(errors='ignore')[-500:]}")
    return result.stdout


def pcm_to_wav(pcm_bytes: bytes, sample_rate: int = 48000, channels: int = 2, sample_width: int = 2) -> bytes:
    """
    py-cord voice receive отдаёт PCM в формате 48kHz / 16-bit / stereo по умолчанию.
    Whisper API ожидает файл с заголовком (WAV), поэтому оборачиваем.
    """
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_bytes)
    return buffer.getvalue()


def play_bytes_in_voice(voice_client: discord.VoiceClient, audio_bytes: bytes, suffix: str = ".mp3", after=None) -> None:
    """
    Проигрывает байты аудио (mp3 от Fish Audio) в уже подключённом voice_client.

    Пишем во временный файл, т.к. FFmpegPCMAudio с pipe=True требует
    файлового дескриптора, а не произвольный BytesIO — так надёжнее всего.
    Временный файл удаляется автоматически после окончания воспроизведения.
    """
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    tmp.write(audio_bytes)
    tmp.close()

    def _cleanup(error):
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
        if after:
            after(error)

    if voice_client.is_playing():
        voice_client.stop()

    source = discord.FFmpegPCMAudio(tmp.name)
    voice_client.play(source, after=_cleanup)
