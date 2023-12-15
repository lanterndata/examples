import { DBQuery } from "@/utils/db";

function normalizeVector(vector) {
  let magnitude = Math.sqrt(vector.reduce((sum, val) => sum + val * val, 0));
  return vector.map((val) => val / magnitude);
}

// Handle the /search endpoint
export default async function handler(req, res) {
  if (req.method === "POST") {
    const { query } = req.body;

    // Get the embedding from cohere
    try {
      const response = await fetch("https://api.cohere.ai/v1/embed", {
        method: "POST",
        headers: {
          accept: "application/json",
          authorization: `Bearer ${process.env.COHERE_API_KEY}`,
          "content-type": "application/json",
        },
        body: JSON.stringify({
          texts: [query],
          truncate: "END",
          model: "embed-multilingual-v2.0",
        }),
      });

      if (!response.ok) {
        throw new Error(`Error: ${response.status}`);
      }

      const data = await response.json();

      // Check if the 'embeddings' field is present in the response
      if (data && data.embeddings) {
        //res.status(200).json({ embeddings: data.embeddings });
        var embedding_vector = data.embeddings[0];
        embedding_vector = normalizeVector(embedding_vector);
      } else {
        throw new Error("Embeddings field not found in the response");
      }
    } catch (error) {
      console.error("Cohere API call failed:", error);
      res.status(500).json({
        error: "Failed to fetch data from Cohere, or embeddings missing",
      });

      return;
    }

    const startTime = new Date();

    // Perform vector search with Lantern
    const TABLE_NAME = "passages2";

    await DBQuery("SET enable_seqscan = false;");

    const embedding_vector_str = `[${embedding_vector.join(",")}]`;

    try {
      const search_query = `SELECT title, text_content, url, cos_dist(emb, ARRAY${embedding_vector_str}) FROM ${TABLE_NAME} ORDER BY emb <=> ARRAY${embedding_vector_str} LIMIT 10;`;
      var { rows } = await DBQuery(search_query);
    } catch (error) {
      console.error("Database query error:", error);
      res.status(500).json({ error: "Internal server error" });
    }

    const endTime = new Date();
    const elapsedTime = endTime - startTime;

    res.status(200).json({
      message: "Search successful",
      query,
      searchTime: elapsedTime,
      results: rows,
    });
  } else {
    // Handle any other HTTP methods
    res.setHeader("Allow", ["POST"]);
    res.status(405).end(`Method ${req.method} Not Allowed`);
  }
}
