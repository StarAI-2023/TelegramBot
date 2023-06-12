import json
import logging

from aiohttp import (
    ClientConnectionError,
    ClientError,
    ClientResponseError,
    ClientSession,
)

import config

logger = logging.getLogger(__name__)


# TODO: make sure to trim content to certain length
class LongTermMemory:
    def __init__(self) -> None:
        self.api_key = config.pinecone_api_key
        self.pinecone_environment = config.pinecone_environment
        self.pinecone_index_name = config.pinecone_index_name
        self.index_name = config.pinecone_index_name
        self.chunk_size = config.pinecone_chunk_size
        self.node_server_password = config.node_server_password
        self.node_server_url = config.node_server_url
        self.session = ClientSession()

    async def similarity_search(self, user_namespace: str, query: str, topK: int = 1):
        """
        {     How the request should look like:
            "indexName":"eugenia",
            "query" : "what's our secret code?",
            "nameSpace": "6041305450",
            "password" : "password in .env file"
        }
        the api end point for search will be <self.node_server_url/search>, and we use post method
        """
        payload: dict[str, str] = {
            "indexName": self.index_name,
            "query": query,
            "nameSpace": user_namespace,
            "password": self.node_server_password,
            "topK": topK,
        }
        headers: dict[str, str] = {"Content-Type": "application/json"}
        searchApiEndPoint = f"{self.node_server_url}/search"

        try:
            async with self.session.post(
                url=searchApiEndPoint, headers=headers, data=json.dumps(payload)
            ) as response:
                print(response)
                if response.status == 200:
                    response_json = await response.json()
                    page_contents: list[str] = [
                        item["pageContent"] for item in response_json
                    ]
                    return page_contents
                else:
                    logger.error(
                        msg=f"Similarity search failed with error, this is the response: {response}"
                    )
                    return None
        except ClientConnectionError:
            logger.error("similarity_search function Connection to Node server failed.")
        except ClientResponseError as error:
            logger.error(
                "similarity_search Invalid response from Node server: %s", error
            )
        except Exception as error:
            logger.error("similarity_search error occurred: %s", error)

    async def add_text(self, user_namespace: str, text):
        """
        How the request should look like:
        {
        "indexName":"eugenia",
        "nameSpace": "6041305450",
        "chunkSize": 2000,
        "password" : "password in .env file",
        "document": {
            "memoryText": "user said: I am so sad!/n you said: I am sorry to hear that. I love you always!/n"
            }
        }
        the api end point for add_text will be <self.node_server_url/upsert>, and we use post method
        document is a dict with key "memoryText" and value is a string
        """
        payload = {
            "indexName": self.index_name,
            "nameSpace": user_namespace,
            "chunkSize": 2000,
            "password": self.node_server_password,
            "document": {
                "memoryText": text
            },  # TODO:Add meta data to document like timestamps
        }
        headers = {"Content-Type": "application/json"}
        upsertApiEndPoint = f"{self.node_server_url}/upsert"

        try:
            async with self.session.post(
                url=upsertApiEndPoint,
                headers=headers,
                data=json.dumps(payload),
            ) as response:
                if response.status == 200:
                    response_json = await response.json()
                    return response_json
                else:
                    logger.error(
                        "Adding text failed with error, status code: %s. Response: %s",
                        response.status,
                        response,
                    )
                    return None
        except ClientConnectionError:
            logger.error("similarity_search function Connection to Node server failed.")
        except ClientResponseError as error:
            logger.error(
                "similarity_search Invalid response from Node server: %s",
                error,
            )
        except Exception as error:
            logger.error("similarity_search error occurred: %s", error)


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
