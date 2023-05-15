# Voice Clone For 11 labs

import aiohttp
import config
import json


class VoiceClone:
    def __init__(self):
        self.api_key = config.voice_clone_api_key
        self.voice_id = config.voice_clone_id
        self.url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}?optimize_streaming_latency=0"

    async def clone_voice(self, text):
        headers = {
            "accept": "audio/mpeg",
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
        }
        data = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {"stability": 0, "similarity_boost": 0},
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.url, headers=headers, data=json.dumps(data)
            ) as resp:
                if resp.status == 200:
                    # Assuming the response is an audio file, read it as bytes
                    audio_data = await resp.read()
                    return audio_data
                else:
                    raise Exception(f"Request failed with status code {resp.status}")


# import asyncio
# print(asyncio.run(VoiceClone().clone_voice("Hello world")))

# result = asyncio.run(VoiceClone().clone_voice("Hello world"))
# print(type(result))

# from pydub import AudioSegment
# from IPython.display import Audio
# import io

# def play_audio(audio_data):
#     audio = AudioSegment.from_file(io.BytesIO(audio_data), format="mp3")
#     return Audio(audio.raw_data, rate=audio.frame_rate)

# voice_clone = VoiceClone()
# audio_data = await voice_clone.clone_voice("Hello world")
# Audio(audio_data)
