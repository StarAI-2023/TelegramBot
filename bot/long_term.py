from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Pinecone

# from langchain.text_splitter import CharacterTextSplitter
# from langchain.document_loaders import TextLoader
import pinecone
import config
import time
import logging

logger = logging.getLogger(__name__)


class LongTermMemory:
    def __init__(self) -> None:
        pinecone.init(
            api_key=config.pinecone_api_key, environment=config.pinecone_environment
        )
        self.user_to_Pinecone = dict()
        self.embeddings = OpenAIEmbeddings(openai_api_key=config.openai_api_key)

    def _get_user_pinecone(self, user_namespace: str):
        # return a langchain Pinecone object with user index
        current_user = str(user_namespace)
        if user_namespace not in self.user_to_Pinecone:
            self.user_to_Pinecone[user_namespace] = Pinecone(
                pinecone.Index(config.pinecone_index_celebrityNmae),
                self.embeddings.embed_query,
                "user_dialog",
                current_user,
            )
        return self.user_to_Pinecone[user_namespace]

    def similarity_search(self, user_namespace: int, query: str):
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
