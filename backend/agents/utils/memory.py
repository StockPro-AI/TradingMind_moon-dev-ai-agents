import chromadb
from chromadb.config import Settings
from openai import OpenAI
import os
import time
import logging

logger = logging.getLogger('backend.agents.utils.memory')


class FinancialSituationMemory:
    """Memory system for storing and retrieving financial situations.

    Features:
    - ChromaDB-backed vector storage
    - TTL-based memory pruning
    - Relevance scoring for memory retrieval
    - Configurable max memory size
    """

    # Default configuration
    DEFAULT_MAX_MEMORIES = 1000
    DEFAULT_TTL_DAYS = 90  # 90 days
    DEFAULT_MIN_RELEVANCE = 0.5  # Minimum similarity score to return

    def __init__(self, name, config):
        self.name = name
        self.enabled = config.get("use_memory", True)
        self.llm_provider = config.get("llm_provider", "openai").lower()

        # Memory management settings
        self.max_memories = config.get("max_memories", self.DEFAULT_MAX_MEMORIES)
        self.ttl_seconds = config.get("memory_ttl_days", self.DEFAULT_TTL_DAYS) * 86400
        self.min_relevance = config.get("min_relevance_score", self.DEFAULT_MIN_RELEVANCE)

        # If memory is disabled, skip initialization
        if not self.enabled:
            self.client = None
            self.chroma_client = None
            self.situation_collection = None
            self.embedding = None
            return

        # Set up embedding model based on provider
        if config.get("backend_url") == "http://localhost:11434/v1":
            self.embedding = "nomic-embed-text"
            self.client = OpenAI(base_url=config["backend_url"])
        elif self.llm_provider == "anthropic":
            # For Anthropic, we still use OpenAI for embeddings since Anthropic doesn't provide embeddings
            # This requires OPENAI_API_KEY to be set
            self.embedding = "text-embedding-3-small"
            openai_key = os.getenv("OPENAI_API_KEY")
            if not openai_key:
                raise ValueError(
                    "When using Anthropic as LLM provider, you still need to set OPENAI_API_KEY "
                    "for embeddings in the memory system. Set it in your .env file or environment. "
                    "Alternatively, set USE_MEMORY=false in .env to disable memory features."
                )
            self.client = OpenAI(api_key=openai_key)
        else:
            # Default to OpenAI for both LLM and embeddings
            self.embedding = "text-embedding-3-small"
            self.client = OpenAI(base_url=config.get("backend_url", "https://api.openai.com/v1"))

        self.chroma_client = chromadb.Client(Settings(allow_reset=True))
        # Use get_or_create_collection to avoid errors when collection already exists
        self.situation_collection = self.chroma_client.get_or_create_collection(name=name)

        # Run initial pruning
        self._prune_old_memories()

    def get_embedding(self, text):
        """Get OpenAI embedding for a single text"""
        if not self.enabled:
            return None

        response = self.client.embeddings.create(
            model=self.embedding, input=text
        )
        return response.data[0].embedding

    def get_embeddings_batch(self, texts):
        """Get OpenAI embeddings for multiple texts in a single API call.

        This is ~50-100x faster than calling get_embedding() in a loop
        because it batches all texts into a single API request.
        """
        if not self.enabled:
            return [None] * len(texts)

        if not texts:
            return []

        # OpenAI's embedding API accepts a list of texts
        response = self.client.embeddings.create(
            model=self.embedding, input=texts
        )
        # Return embeddings in the same order as input texts
        return [item.embedding for item in sorted(response.data, key=lambda x: x.index)]

    def add_situations(self, situations_and_advice):
        """Add financial situations and their corresponding advice.

        Parameter is a list of tuples (situation, rec).
        Each memory is timestamped for TTL-based pruning.
        """
        if not self.enabled:
            return  # Skip if memory is disabled

        if not situations_and_advice:
            return

        # Check if we need to prune before adding
        current_count = self.situation_collection.count()
        if current_count + len(situations_and_advice) > self.max_memories:
            self._prune_to_limit(self.max_memories - len(situations_and_advice))

        situations = []
        advice = []
        ids = []
        current_time = time.time()

        offset = self.situation_collection.count()

        for i, (situation, recommendation) in enumerate(situations_and_advice):
            situations.append(situation)
            advice.append(recommendation)
            ids.append(str(offset + i))

        # Use batch embedding for ~50-100x speedup
        embeddings = self.get_embeddings_batch(situations)

        # Add timestamp metadata for TTL pruning
        metadatas = [
            {"recommendation": rec, "timestamp": current_time}
            for rec in advice
        ]

        self.situation_collection.add(
            documents=situations,
            metadatas=metadatas,
            embeddings=embeddings,
            ids=ids,
        )

        logger.debug(f"Added {len(situations)} memories to {self.name} (total: {self.situation_collection.count()})")

    def get_memories(self, current_situation, n_matches=1):
        """Find matching recommendations using OpenAI embeddings.

        Filters results by minimum relevance score and excludes expired memories.
        """
        if not self.enabled:
            return []  # Return empty list if memory is disabled

        if self.situation_collection.count() == 0:
            return []

        query_embedding = self.get_embedding(current_situation)

        # Request more results than needed to account for filtering
        results = self.situation_collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_matches * 2, self.situation_collection.count()),
            include=["metadatas", "documents", "distances"],
        )

        current_time = time.time()
        matched_results = []

        for i in range(len(results["documents"][0])):
            similarity_score = 1 - results["distances"][0][i]
            metadata = results["metadatas"][0][i]

            # Filter by minimum relevance
            if similarity_score < self.min_relevance:
                continue

            # Filter expired memories (if timestamp exists)
            timestamp = metadata.get("timestamp", 0)
            if timestamp > 0 and (current_time - timestamp) > self.ttl_seconds:
                continue

            matched_results.append(
                {
                    "matched_situation": results["documents"][0][i],
                    "recommendation": metadata["recommendation"],
                    "similarity_score": similarity_score,
                    "age_days": (current_time - timestamp) / 86400 if timestamp else None,
                }
            )

            # Stop once we have enough results
            if len(matched_results) >= n_matches:
                break

        return matched_results

    def _prune_old_memories(self):
        """Remove memories older than TTL."""
        if not self.enabled or self.situation_collection.count() == 0:
            return

        current_time = time.time()
        cutoff_time = current_time - self.ttl_seconds

        try:
            # Get all memories with timestamps
            all_data = self.situation_collection.get(include=["metadatas"])

            if not all_data["ids"]:
                return

            # Find expired memories
            expired_ids = []
            for i, metadata in enumerate(all_data["metadatas"]):
                timestamp = metadata.get("timestamp", 0)
                if timestamp > 0 and timestamp < cutoff_time:
                    expired_ids.append(all_data["ids"][i])

            # Delete expired memories
            if expired_ids:
                self.situation_collection.delete(ids=expired_ids)
                logger.info(f"Pruned {len(expired_ids)} expired memories from {self.name}")

        except Exception as e:
            logger.warning(f"Error pruning memories from {self.name}: {e}")

    def _prune_to_limit(self, target_count: int):
        """Prune oldest memories to reach target count."""
        if not self.enabled:
            return

        current_count = self.situation_collection.count()
        if current_count <= target_count:
            return

        try:
            # Get all memories with timestamps
            all_data = self.situation_collection.get(include=["metadatas"])

            if not all_data["ids"]:
                return

            # Sort by timestamp (oldest first)
            items = list(zip(all_data["ids"], all_data["metadatas"]))
            items.sort(key=lambda x: x[1].get("timestamp", 0))

            # Calculate how many to remove
            to_remove = current_count - target_count
            ids_to_remove = [item[0] for item in items[:to_remove]]

            if ids_to_remove:
                self.situation_collection.delete(ids=ids_to_remove)
                logger.info(f"Pruned {len(ids_to_remove)} oldest memories from {self.name}")

        except Exception as e:
            logger.warning(f"Error pruning memories from {self.name}: {e}")

    def get_stats(self) -> dict:
        """Get memory statistics."""
        if not self.enabled:
            return {"enabled": False}

        count = self.situation_collection.count()

        return {
            "enabled": True,
            "name": self.name,
            "count": count,
            "max_memories": self.max_memories,
            "ttl_days": self.ttl_seconds / 86400,
            "min_relevance": self.min_relevance,
        }

    def clear(self):
        """Clear all memories."""
        if not self.enabled:
            return

        self.chroma_client.delete_collection(self.name)
        self.situation_collection = self.chroma_client.get_or_create_collection(name=self.name)
        logger.info(f"Cleared all memories from {self.name}")


if __name__ == "__main__":
    # Example usage
    matcher = FinancialSituationMemory()

    # Example data
    example_data = [
        (
            "High inflation rate with rising interest rates and declining consumer spending",
            "Consider defensive sectors like consumer staples and utilities. Review fixed-income portfolio duration.",
        ),
        (
            "Tech sector showing high volatility with increasing institutional selling pressure",
            "Reduce exposure to high-growth tech stocks. Look for value opportunities in established tech companies with strong cash flows.",
        ),
        (
            "Strong dollar affecting emerging markets with increasing forex volatility",
            "Hedge currency exposure in international positions. Consider reducing allocation to emerging market debt.",
        ),
        (
            "Market showing signs of sector rotation with rising yields",
            "Rebalance portfolio to maintain target allocations. Consider increasing exposure to sectors benefiting from higher rates.",
        ),
    ]

    # Add the example situations and recommendations
    matcher.add_situations(example_data)

    # Example query
    current_situation = """
    Market showing increased volatility in tech sector, with institutional investors 
    reducing positions and rising interest rates affecting growth stock valuations
    """

    try:
        recommendations = matcher.get_memories(current_situation, n_matches=2)

        for i, rec in enumerate(recommendations, 1):
            print(f"\nMatch {i}:")
            print(f"Similarity Score: {rec['similarity_score']:.2f}")
            print(f"Matched Situation: {rec['matched_situation']}")
            print(f"Recommendation: {rec['recommendation']}")

    except Exception as e:
        print(f"Error during recommendation: {str(e)}")
