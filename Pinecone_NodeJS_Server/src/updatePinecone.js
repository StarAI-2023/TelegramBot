import { OpenAIEmbeddings } from "langchain/embeddings/openai";
import { RecursiveCharacterTextSplitter } from "langchain/text_splitter";
import { Document } from "langchain/document";
import { PineconeStore } from "langchain/vectorstores/pinecone";

// document is an object with the following structure:
// {
//   metadata: {}, //TODO(vincex): define and insert metadata field into pinecone
//   memoryText: string,
// }
export const updatePinecone = async (
  client,
  indexName,
  nameSpace,
  chunkSize,
  document
) => {
  const index = client.Index(indexName);
  const memoryText = document.memoryText;
  const textSplitter = new RecursiveCharacterTextSplitter({
    chunkSize: validateChunkSize(chunkSize),
  });
  // Split document into chunks
  //TODO: add metadata to each chunk
  const chunks = await textSplitter.createDocuments([memoryText]);

  // Store into pinecone
  const vectorStore = await PineconeStore.fromExistingIndex(
    new OpenAIEmbeddings(),
    { pineconeIndex: index, namespace: nameSpace }
  );
  return await vectorStore.addDocuments(chunks);
};

function validateChunkSize(size) {
  if (!Number.isInteger(size)) {
    throw new Error("chunkSize must be an integer");
  }
  return size;
}
