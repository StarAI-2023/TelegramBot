import { OpenAIEmbeddings } from "langchain/embeddings/openai";
import { PineconeStore } from "langchain/vectorstores/pinecone";

export const queryPineconeVectorStore = async (
  client,
  indexName,
  nameSpace,
  query,
  topK = 5
) => {
  // const index = client.Index(indexName);
  // const queryEmbedding = await new OpenAIEmbeddings().embedQuery(query);
  // let queryResponse = await index.query({
  //   queryRequest: {
  //     namespace: nameSpace,
  //     topK: 6,
  //     vector: queryEmbedding,
  //     includeMetadata: true,
  //     includeValues: true,
  //   },
  // });
  // return queryResponse;

  // // TODO(vincex): rank response based on metadata
  // return queryResponse;

  const index = client.Index(indexName);
  const vectorStore = await PineconeStore.fromExistingIndex(
    new OpenAIEmbeddings(),
    { pineconeIndex: index, namespace: nameSpace }
  );

  /* Search the vector DB independently with meta filters */
  const results = await vectorStore.similaritySearch(query, topK);

  return results;
};
