# import config
# import aiohttp
# import json
# import asyncio
# from langchain.embeddings.openai import OpenAIEmbeddings

# class test:
#     def __init__(self):
#         self.api_key = config.pinecone_api_key
#         self.voice_id = config.pinecone_environment
#         self.url: LiteralString = f"https://idka-5346b9a.svc.us-west1-gcp-free.pinecone.io/query"

#     async def query(self, query, namespace,topk, filter = None,):
#         headers = {
#             "Accept": "application/json",
# "Content-Type": "application/json",
# "Api-Key": self.api_key,
# "Host": "idka-5346b9a.svc.us-west1-gcp-free.pinecone.io",
#         }
#         body = {
#             "namespace": namespace,
#             "topK": topk,
#             "filter": filter,
#             "includeMetadata": True,
#             "includeValues": True,
#             "Vector": query,
#         }
#         async with aiohttp.ClientSession() as session:
#             async with session.post(
#                 self.url, headers=headers, body=json.dumps(body)
#             ) as resp:
#                 if resp.status == 200:
#                     # Assuming the response is an audio file, read it as bytes
#                     data = await resp.read()
#                     print(data)
#                     return data
#                 else:
#                     raise Exception(f"Request failed with status code {resp.status}")
                
# embeddings = OpenAIEmbeddings(openai_api_key=config.openai_api_key).embed_query
# a = test()
# # asyncio.run(a.query([embeddings("what is our secret code")],"6041305450"),topk=1)

                


