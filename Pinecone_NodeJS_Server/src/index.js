import { PineconeClient } from "@pinecone-database/pinecone";
import * as dotenv from "dotenv";
import { createPineconeIndex } from "./createPineconeIndex.js";
import { updatePinecone } from "./updatePinecone.js";
import { queryPineconeVectorStore } from "./queryPinecone.js";
import express from "express";

import bodyParser from "body-parser";

dotenv.config();

const app = express();
app.use(bodyParser.json());

// Initialize Pinecone client
let client;
(async () => {
  try {
    client = new PineconeClient();
    await client.init({
      apiKey: process.env.PINECONE_API_KEY,
      environment: process.env.PINECONE_ENVIRONMENT,
    });
  } catch (error) {
    console.log("Pinecone client init failed with error: " + error);
  }
})();

// api for similarity search
app.post("/search", async (req, res) => {
  const { password, indexName, nameSpace, query } = req.body;

  if (!password || !indexName || !query || !nameSpace) {
    return res.status(400).json({
      error: "password, indexName, query, and nameSpace are required fields.",
    });
  }
  if (password !== process.env.PASSWORD) {
    return res.status(403).json({
      error: "Invalid password.",
    });
  }

  try {
    const result = await queryPineconeVectorStore(
      client,
      indexName,
      nameSpace,
      query
    );
    res.status(200).json(result);
  } catch (error) {
    res.status(500).json({
      error: error.toString(),
    });
  }
});

// Api for upserting documents.
// docString will be a long string of text.
app.post("/upsert", async (req, res) => {
  const { password, indexName, nameSpace, document, chunkSize } = req.body;

  if (!password || !indexName || !document || !nameSpace || !chunkSize) {
    return res.status(400).json({
      error:
        "password, indexName, question, nameSpace, and chunkSize are required fields.",
    });
  }
  if (password !== process.env.PASSWORD) {
    return res.status(403).json({
      error: "Invalid password.",
    });
  }

  try {
    const result = await updatePinecone(
      client,
      indexName,
      nameSpace,
      chunkSize,
      document
    );
    res.status(200).json(result);
  } catch (error) {
    res.status(500).json({
      error: error.toString(),
    });
  }
});

app.post("/createIndex", async (req, res) => {
  const { password, indexName } = req.body;

  if (!password || !indexName) {
    return res.status(400).json({
      error: "password and indexName are required fields.",
    });
  }
  if (password !== process.env.PASSWORD) {
    return res.status(403).json({
      error: "Invalid password.",
    });
  }

  try {
    const vectorDimension = 1536;
    const result = await createPineconeIndex(
      client,
      indexName,
      vectorDimension
    );
    res.json(result);
  } catch (error) {
    res.status(500).json({
      error: error.toString(),
    });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
