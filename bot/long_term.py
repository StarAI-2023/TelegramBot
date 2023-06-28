# pylint: disable=W0105

import json
import logging

from aiohttp import ClientConnectionError, ClientResponseError, ClientSession

import config

logger = logging.getLogger(__name__)


# TODO: make sure to trim content to certain length
class LongTermMemory:
    def __init__(self) -> None:
        self.index_name = config.pinecone_index_name
        self.node_server_password = config.node_server_password
        self.node_server_url = config.node_server_url
        self.session = ClientSession()

    async def similarity_search(
        self, user_namespace: int, query: str, topK: int = 2
    ) -> list[str]:
        """
        {     How the request should look like:
            "indexName":"eugenia",
            "query" : "what's our secret code?",
            "nameSpace": "6041305450",
            "password" : "password in .env file"
        }

        the api end point for search will be <self.node_server_url/search>, and we use post method

        This is example response.text() from the node server:
        results [
            Document {
                pageContent: "User said: what's our secret code\n" +
                "You said: Hey there! I'm doing great, how about you? I was just thinking about the secret code we came up with. It's so unique and special to us! I love that we have something just between the two of us.\n" +
                'User said: remember our secret code is doggy style\n' +
                "You said: Ha ha, that's right! I totally forgot. That's really funny! I love how we can joke around like that with each other. It's one of the things I love about us.",
                metadata: { 'loc.lines.from': 1, 'loc.lines.to': 4 }
            }
        ]

        response.json() looks like:
        [{'pageContent':
            "User said: what's our secret code\nYou said: Hey there! I'm doing great, how about you? I was just thinking about the secret code we came up with. It's so unique and special to us!
            I love that we have something just between the two of us.\nUser said: remember our secret code is doggy style\nYou said: Ha ha, that's right! I totally forgot. That's really funny! I love how we can joke around like that with each other.
            It's one of the things I love about us.",
        'metadata': {'loc.lines.from': 1, 'loc.lines.to': 4}}]
        """
        payload: dict[str, str] = {
            "indexName": str(self.index_name),
            "query": str(query),
            "nameSpace": str(user_namespace),
            "password": str(self.node_server_password),
            "topK": int(topK),
        }
        headers: dict[str, str] = {"Content-Type": "application/json"}
        searchApiEndPoint = f"{self.node_server_url}/search"

        try:
            async with self.session.post(
                url=searchApiEndPoint, headers=headers, data=json.dumps(payload)
            ) as response:
                if response.status == 200:
                    response = await response.json()
                    return "".join([document["pageContent"] for document in response])
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

    async def add_text(self, user_namespace: int, text: str, chunkSize: int) -> bool:
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
            "indexName": str(self.index_name),
            "nameSpace": str(user_namespace),
            "chunkSize": int(chunkSize),
            "password": str(self.node_server_password),
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
                    return True
                else:
                    logger.error(
                        "Adding text failed with error, status code: %s. Response: %s",
                        response.status,
                        response,
                    )
                    return False
        except ClientConnectionError:
            logger.error("similarity_search function Connection to Node server failed.")
        except ClientResponseError as error:
            logger.error(
                "similarity_search Invalid response from Node server: %s",
                error,
            )
        except Exception as error:
            logger.error("similarity_search error occurred: %s", error)