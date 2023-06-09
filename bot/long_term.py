from langchain.embeddings.openai import OpenAIEmbeddings

# from langchain.text_splitter import CharacterTextSplitter
# from langchain.document_loaders import TextLoader
import pinecone
import config
import time
import logging
import uuid
import aiohttp
import json

from typing import Any, Callable, Iterable, List, Optional, Tuple
from langchain.embeddings.base import Embeddings

from langchain.docstore.document import Document
from langchain.vectorstores.base import VectorStore

import test

logger = logging.getLogger(__name__)


class LongTermMemory:
    def __init__(self) -> None:
        pinecone.init(
            api_key=config.pinecone_api_key, environment=config.pinecone_environment
        )
        self.user_to_Pinecone = dict()
        self.embeddings = OpenAIEmbeddings(openai_api_key=config.openai_api_key)
        self.index = pinecone.Index(config.pinecone_index_name)

    def _get_user_pinecone(self, user_namespace: str):
        # return a langchain Pinecone object with user index
        current_user = str(user_namespace)
        if user_namespace not in self.user_to_Pinecone:
            self.user_to_Pinecone[user_namespace] = Pinecone(
                self.index,
                self.embeddings.embed_query,
                "user_dialog",
                current_user,
            )
        return self.user_to_Pinecone[user_namespace]

    async def similarity_search(self, user_namespace: int, query: str):
        functionStartTime = time.perf_counter()
        current_user = str(user_namespace)
        docs = await self._get_user_pinecone(current_user).similarity_search(query, k=1)
        functionEndTime = time.perf_counter()
        logger.error(
            msg=f"pinecone similarity_search elapsed time: {functionEndTime-functionStartTime} seconds."
        )
        return [doc.page_content for doc in docs]

    def add_text(self, user_namespace: int, text):
        current_user = str(object=user_namespace)
        # text = a list of str,  upsert to pinecone individually
        self._get_user_pinecone(current_user).add_texts(text)


class Pinecone(VectorStore):
    """Wrapper around Pinecone vector database.

    To use, you should have the ``pinecone-client`` python package installed.

    Example:
        .. code-block:: python

            from langchain.vectorstores import Pinecone
            from langchain.embeddings.openai import OpenAIEmbeddings
            import pinecone

            # The environment should be the one specified next to the API key
            # in your Pinecone console
            pinecone.init(api_key="***", environment="...")
            index = pinecone.Index("langchain-demo")
            embeddings = OpenAIEmbeddings()
            vectorstore = Pinecone(index, embeddings.embed_query, "text")
    """

    def __init__(
        self,
        index: Any,
        embedding_function: Callable,
        text_key: str,
        namespace: Optional[str] = None,
    ):
        """Initialize with Pinecone client."""
        try:
            import pinecone
        except ImportError:
            raise ValueError(
                "Could not import pinecone python package. "
                "Please install it with `pip install pinecone-client`."
            )
        if not isinstance(index, pinecone.index.Index):
            raise ValueError(
                f"client should be an instance of pinecone.index.Index, "
                f"got {type(index)}"
            )
        self._index = index
        self._embedding_function = embedding_function
        self._text_key = text_key
        self._namespace = namespace

    def add_texts(
        self,
        texts: Iterable[str],
        metadatas: Optional[List[dict]] = None,
        ids: Optional[List[str]] = None,
        namespace: Optional[str] = None,
        batch_size: int = 32,
        **kwargs: Any,
    ) -> List[str]:
        """Run more texts through the embeddings and add to the vectorstore.

        Args:
            texts: Iterable of strings to add to the vectorstore.
            metadatas: Optional list of metadatas associated with the texts.
            ids: Optional list of ids to associate with the texts.
            namespace: Optional pinecone namespace to add the texts to.

        Returns:
            List of ids from adding the texts into the vectorstore.

        """
        if namespace is None:
            namespace = self._namespace
        # Embed and create the documents
        docs = []
        ids = ids or [str(uuid.uuid4()) for _ in texts]
        for i, text in enumerate(texts):
            embedding = self._embedding_function(text)
            metadata = metadatas[i] if metadatas else {}
            metadata[self._text_key] = text
            docs.append((ids[i], embedding, metadata))
        # upsert to Pinecone
        self._index.upsert(vectors=docs, namespace=namespace, batch_size=batch_size)
        return ids

    async def similarity_search_with_score(
        self,
        query: str,
        k: int = 4,
        filter: Optional[dict] = None,
        namespace: Optional[str] = None,
    ) -> List[Tuple[Document, float]]:
        """Return pinecone documents most similar to query, along with scores.

        Args:
            query: Text to look up documents similar to.
            k: Number of Documents to return. Defaults to 4.
            filter: Dictionary of argument(s) to filter on metadata
            namespace: Namespace to search in. Default will search in '' namespace.

        Returns:
            List of Documents most similar to the query and score for each
        """
        if namespace is None:
            namespace = self._namespace
        query_obj = self._embedding_function(query)
        docs = []
        print("in")
        results = await test().query(
            [query_obj],
            namespace=namespace,
            topk=k,
            filter=filter,
        )
        print("out")
        for res in results["matches"]:
            metadata = res["metadata"]
            if self._text_key in metadata:
                text = metadata.pop(self._text_key)
                score = res["score"]
                docs.append((Document(page_content=text, metadata=metadata), score))
            else:
                logger.warning(
                    f"Found document with no `{self._text_key}` key. Skipping."
                )
        return docs

    async def similarity_search(
        self,
        query: str,
        k: int = 4,
        filter: Optional[dict] = None,
        namespace: Optional[str] = None,
        **kwargs: Any,
    ) -> List[Document]:
        """Return pinecone documents most similar to query.

        Args:
            query: Text to look up documents similar to.
            k: Number of Documents to return. Defaults to 4.
            filter: Dictionary of argument(s) to filter on metadata
            namespace: Namespace to search in. Default will search in '' namespace.

        Returns:
            List of Documents most similar to the query and score for each
        """
        docs_and_scores = await self.similarity_search_with_score(
            query, k=k, filter=filter, namespace=namespace, **kwargs
        )
        return [doc for doc, _ in docs_and_scores]
    
    @classmethod
    def from_texts(
        cls,
        texts: List[str],
        embedding: Embeddings,
        metadatas: Optional[List[dict]] = None,
        ids: Optional[List[str]] = None,
        batch_size: int = 32,
        text_key: str = "text",
        index_name: Optional[str] = None,
        namespace: Optional[str] = None,
        **kwargs: Any,
    ):
        """Construct Pinecone wrapper from raw documents.

        This is a user friendly interface that:
            1. Embeds documents.
            2. Adds the documents to a provided Pinecone index

        This is intended to be a quick way to get started.

        Example:
            .. code-block:: python

                from langchain import Pinecone
                from langchain.embeddings import OpenAIEmbeddings
                import pinecone

                # The environment should be the one specified next to the API key
                # in your Pinecone console
                pinecone.init(api_key="***", environment="...")
                embeddings = OpenAIEmbeddings()
                pinecone = Pinecone.from_texts(
                    texts,
                    embeddings,
                    index_name="langchain-demo"
                )
        """
        try:
            import pinecone
        except ImportError:
            raise ValueError(
                "Could not import pinecone python package. "
                "Please install it with `pip install pinecone-client`."
            )

        indexes = pinecone.list_indexes()  # checks if provided index exists

        if index_name in indexes:
            index = pinecone.Index(index_name)
        elif len(indexes) == 0:
            raise ValueError(
                "No active indexes found in your Pinecone project, "
                "are you sure you're using the right API key and environment?"
            )
        else:
            raise ValueError(
                f"Index '{index_name}' not found in your Pinecone project. "
                f"Did you mean one of the following indexes: {', '.join(indexes)}"
            )

        for i in range(0, len(texts), batch_size):
            # set end position of batch
            i_end = min(i + batch_size, len(texts))
            # get batch of texts and ids
            lines_batch = texts[i:i_end]
            # create ids if not provided
            if ids:
                ids_batch = ids[i:i_end]
            else:
                ids_batch = [str(uuid.uuid4()) for n in range(i, i_end)]
            # create embeddings
            embeds = embedding.embed_documents(lines_batch)
            # prep metadata and upsert batch
            if metadatas:
                metadata = metadatas[i:i_end]
            else:
                metadata = [{} for _ in range(i, i_end)]
            for j, line in enumerate(lines_batch):
                metadata[j][text_key] = line
            to_upsert = zip(ids_batch, embeds, metadata)

            # upsert to Pinecone
            index.upsert(vectors=list(to_upsert), namespace=namespace)
        return cls(index, embedding.embed_query, text_key, namespace)

    @classmethod
    def from_existing_index(
        cls,
        index_name: str,
        embedding: Embeddings,
        text_key: str = "text",
        namespace: Optional[str] = None,
    ):
        """Load pinecone vectorstore from index name."""
        try:
            import pinecone
        except ImportError:
            raise ValueError(
                "Could not import pinecone python package. "
                "Please install it with `pip install pinecone-client`."
            )

        return cls(
            pinecone.Index(index_name), embedding.embed_query, text_key, namespace
        )
        
class test:
    def __init__(self):
        self.api_key = config.pinecone_api_key
        self.voice_id = config.pinecone_environment
        self.url: LiteralString = f"https://idka-5346b9a.svc.us-west1-gcp-free.pinecone.io/query"

    async def query(self, query, namespace,topk, filter = None,):
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Api-Key": self.api_key,
            "Host": "idka-5346b9a.svc.us-west1-gcp-free.pinecone.io",
        }
        body = {
            "namespace": namespace,
            "topK": topk,
            "filter": filter,
            "includeMetadata": True,
            "vector": query,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.url, headers=headers, data=json.dumps(body)
            ) as resp:
                if resp.status == 200:
                    # Assuming the response is an audio file, read it as bytes
                    data = await resp.read()
                    print(data)
                    return data
                else:
                    print(resp.reason)
                    raise Exception(f"Request failed with status code {resp.status}")