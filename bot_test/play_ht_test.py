# from io import BytesIO
# import requests

# url = "https://play.ht/api/v2/tts/stream"

# async def test():
#     payload = {
#         "quality": "draft",
#         "output_format": "mp3",
#         "speed": 1,
#         "sample_rate": 24000,
#         "text": "shit",
#         "voice": "s3://voice-cloning-zero-shot/fd3dfff1-aa41-4bf5-8604-ab9e15bd4810/w3r/manifest.json"
#     }
#     headers = {
#         "accept": "audio/mpeg",
#         "content-type": "application/json",
#         "AUTHORIZATION": "Bearer d5cfd08b9317422a970d626125caa556",
#         "X-USER-ID": "1J9LGMVYhkO5wy7trCodKgjOQ8l1"
#     }

#     await requests.post(url, json=payload, headers=headers)

#     return BytesIO(response.content)

# with open('output.mp3', 'wb') as out_file:
#     out_file.write(audio.read())
    
    
# stress test for search api 
import asyncio
import aiohttp
import time
import json
from io import BytesIO
search_url = "https://play.ht/api/v2/tts/stream"

search_payload = {
    "quality": "premium",
        "output_format": "mp3",
        "speed": 1,
        "sample_rate": 24000,
        "text": "I am good and want to take a shit",
        "voice": "s3://voice-cloning-zero-shot/fd3dfff1-aa41-4bf5-8604-ab9e15bd4810/w3r/manifest.json"
    }

headers = {
    "accept": "audio/mpeg",
    "content-type": "application/json",
    "AUTHORIZATION": "Bearer a65d351aba794e7fb4d6f17162311025",
    "X-USER-ID": "lUTFPtLCfiP68Bbw0EV4dVJQD5n2"
}

async def make_request(session, url, headers, payload,count):
    start_time = time.perf_counter()
    async with session.post(url, headers=headers, data=json.dumps(payload)) as response:
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        audio = BytesIO(await response.read())
        if (response.status == 200):
            with open(f'shit/output{count}.mp3', 'wb') as out_file:
                out_file.write(audio.read())
            return True, elapsed_time > 3
        return False, elapsed_time > 3

async def main():
    start_time = time.perf_counter()
    successful_requests = 0
    slow_requests = 0
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(1000):
            tasks.append(make_request(session, search_url, headers, search_payload,i))
        results = await asyncio.gather(*tasks)
        for was_successful, was_slow in results:
            if was_successful:
                successful_requests += 1
            if was_slow:
                slow_requests += 1
                
    end_time = time.perf_counter()
    print(f'Total time: {end_time - start_time} seconds')
    print(f'Successful requests: {successful_requests}')
    print(f'Slow requests: {slow_requests}')

import nest_asyncio
nest_asyncio.apply()

loop = asyncio.get_event_loop()
loop.run_until_complete(main())