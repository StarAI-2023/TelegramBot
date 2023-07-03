import aiohttp
import config
import json


# 11 lab default voice
class VoiceClone:
    def __init__(self):
        self.api_key = config.voice_clone_api_key
        self.voice_id = config.voice_clone_id
        self.url = "https://api.play.ht/api/v2/tts/stream"

    async def generateVoice(self, text) -> bytes:
        headers = {
            "accept": "audio/mpeg",
            "content-type": "application/json",
            "AUTHORIZATION": f"Bearer {self.api_key}",
            "X-USER-ID": self.voice_id
        }
        data = {
            "quality": "draft",
            "output_format": "mp3",
            "speed": 1,
            "sample_rate": 24000,
            "text": text,
            "voice": "s3://voice-cloning-zero-shot/4dd4a3e7-5359-42ad-b895-bc0335e55503/eugenia-non-hf/manifest.json"
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

# from typing import Iterator, Union
# from elevenlabs import clone, generate, play, set_api_key
# import config
# import os


# class VoiceClone:
#     def __init__(self) -> None:
#         set_api_key(config.voice_clone_api_key)
#         self.voice = clone(
#             name="Shab",
#             description="Shab",
#             files=self.getVoiceSamplesFiles(),
#         )
#         # # low stability will make the voice fluctuate more, thus more emotional
#         # self.voice.settings.stability = 0.23
#         # self.voice.settings.similarity_boost = 0.9

#     def getVoiceSamplesFiles(
#         self,
#         voice_samples_path="bot/voice_samples/Shab",
#     ) -> list:
#         file_list = []

#         # Check if the directory exists
#         if os.path.exists(voice_samples_path):
#             # Iterate over all files in the directory
#             for file_name in os.listdir(voice_samples_path):
#                 file_path = os.path.join(voice_samples_path, file_name)
#                 if os.path.isfile(file_path):
#                     file_list.append(file_path)
#         else:
#             print(
#                 "Directory path does not exist, and current directory is:" + os.getcwd()
#             )
#             raise

#         return file_list

#     async def generateVoice(self, textToClone: str) -> Union[bytes, Iterator[bytes]]:
#         audio = generate(text=textToClone, voice=self.voice)
#         return audio


# import asyncio
# from io import BytesIO
# from voice_clone import VoiceClone


# async def main():
#     voice_clone = VoiceClone()
#     print(voice_clone.getVoiceSamplesFiles())
#     audio_data = await voice_clone.generateVoice("answer")
#     audio_file = BytesIO(audio_data)
#     audio_file.name = "output.mp3"
#     print(audio_file)


# if __name__ == "__main__":
#     asyncio.run(main())