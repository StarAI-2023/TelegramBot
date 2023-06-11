import logging
import time

import aiohttp

import config

logger = logging.getLogger(__name__)


class LongTermMemory:
    def __init__(self) -> None:
        self.api_key = config.pinecone_api_key
        self.pinecone_environment = config.pinecone_environment
        self.pinecone_index_name = config.pinecone_index_name
        self.indexName = config.pinecone_index_name
        self.chunkSize = config.pinecone_chunk_size
        self.node_server_password = config.node_server_password
        self.noder_server_url = config.node_server_url

    async def similarity_search(self, user_namespace: int, query: str):
        url = "http://localhost:3000/search"
        payload = {
            "indexName": "idka",
            "query": "Taylor switft",
            "nameSpace": "6041305450",
            "password": "fhawjthaj-hthjerahr234oru0ufhgarp324ytp98ayfpsdayfuh4wiu",
        }
        headers = {"Content-Type": "application/json"}
        # TODO: make sure to trim content to certain length
        functionStartTime = time.perf_counter()
        current_user = str(user_namespace)
        docs = self._get_user_pinecone(current_user).similarity_search(query, k=1)
        functionEndTime = time.perf_counter()
        logger.error(
            msg=f"pinecone similarity_search elapsed time: {functionEndTime-functionStartTime} seconds."
        )
        return [doc.page_content for doc in docs]

    def add_text(self, user_namespace: int, text):
        current_user = str(object=user_namespace)
        # text = a list of str,  upsert to pinecone individually
        self._get_user_pinecone(current_user).add_texts(text)


# class LongTermMemory:
#     def __init__(self) -> None:
#         self.api_key = config.pinecone_api_key
#         self.pinecone_environment = config.pinecone_environment

#         self.user_to_Pinecone = dict()
#         self.embeddings = OpenAIEmbeddings(openai_api_key=config.openai_api_key)
#         self.index = pinecone.Index(config.pinecone_index_name)

#     def _get_user_pinecone(self, user_namespace: str):
#         # return a langchain Pinecone object with user index
#         current_user = str(user_namespace)
#         if user_namespace not in self.user_to_Pinecone:
#             self.user_to_Pinecone[user_namespace] = Pinecone(
#                 self.index,
#                 self.embeddings.embed_query,
#                 "user_dialog",
#                 current_user,
#             )
#         return self.user_to_Pinecone[user_namespace]

#     def similarity_search(self, user_namespace: int, query: str):
#         # TODO(vincex): make sure to trim content to certain length
#         functionStartTime = time.perf_counter()
#         current_user = str(user_namespace)
#         docs = self._get_user_pinecone(current_user).similarity_search(query, k=1)
#         functionEndTime = time.perf_counter()
#         logger.error(
#             msg=f"pinecone similarity_search elapsed time: {functionEndTime-functionStartTime} seconds."
#         )
#         return [doc.page_content for doc in docs]

#     def add_text(self, user_namespace: int, text):
#         current_user = str(object=user_namespace)
#         # text = a list of str,  upsert to pinecone individually
#         self._get_user_pinecone(current_user).add_texts(text)
