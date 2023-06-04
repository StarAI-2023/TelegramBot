from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Pinecone
# from langchain.text_splitter import CharacterTextSplitter
# from langchain.document_loaders import TextLoader
import pinecone
import config

class LongTermMemory():
    def __init__(self) -> None:
        pinecone.init(api_key=config.pinecone_api_key, environment=config.pinecone_environment)
        self.user_to_Pinecone = dict()
        self.embeddings = OpenAIEmbeddings(openai_api_key=config.openai_api_key)

    def _get_user_pinecone(self,user_id:str):
        #return a langchain Pinecone object with user index
        if user_id not in self.user_to_index:
            self.user_to_Pinecone[user_id] = Pinecone.from_existing_index(user_id,self.embeddings)
        return self.user_to_index[user_id]
    
    def add_new_user(self,user_id: int):
        current_user = str(user_id)
        pinecone.create_index(current_user, dimension=1024)
        self.user_to_Pinecone[current_user] = Pinecone(pinecone.Index(current_user),self.embeddings)
        
    def similarity_search(self, user_id: int, query: str):
        current_user = str(user_id)
        docs = self._get_user_pinecone(current_user).similarity_search(query)
        return "".join([doc.content for doc in docs])
    
    def add_text(self,user_id: int, text):
        current_user = str(user_id)
        #text = a list of str,  upsert to pinecone individually
        self._get_user_pinecone(current_user).add_texts(text)