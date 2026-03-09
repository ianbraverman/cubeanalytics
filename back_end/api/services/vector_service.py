import chromadb
import os
from typing import Optional

class VectorService:
    """Service for managing vector embeddings in Chroma DB."""
    
    # Initialize Chroma client - using persistent storage
    CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_data")
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection_name = "card_feedback"
    
    @classmethod
    def get_collection(cls):
        """Get or create the card feedback collection."""
        return cls.client.get_or_create_collection(
            name=cls.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
    
    @classmethod
    def add_feedback_vector(
        cls,
        feedback_id: int,
        card_name: str,
        feedback_text: str,
        feedback_type: str,
        rating: int,
        user_id: int
    ) -> str:
        """Add a feedback vector to Chroma DB."""
        collection = cls.get_collection()
        
        # Combine all text data for embedding
        combined_text = f"{card_name} {feedback_type} {feedback_text}"
        
        # Create a unique ID for this feedback in Chroma
        vector_id = f"feedback_{feedback_id}"
        
        # Add to collection with metadata
        collection.add(
            ids=[vector_id],
            documents=[combined_text],
            metadatas=[{
                "feedback_id": str(feedback_id),
                "card_name": card_name,
                "feedback_type": feedback_type,
                "rating": str(rating),
                "user_id": str(user_id)
            }]
        )
        
        return vector_id
    
    @classmethod
    def query_similar_feedback(
        cls,
        query_text: str,
        feedback_type: Optional[str] = None,
        n_results: int = 5
    ) -> dict:
        """Query similar feedback vectors from Chroma DB."""
        collection = cls.get_collection()
        
        where_filter = None
        if feedback_type:
            where_filter = {"feedback_type": {"$eq": feedback_type}}
        
        results = collection.query(
            query_texts=[query_text],
            where=where_filter,
            n_results=n_results
        )
        
        return results
    
    @classmethod
    def get_feedback_by_card(
        cls,
        card_name: str,
        feedback_type: Optional[str] = None,
        n_results: int = 10
    ) -> dict:
        """Get all feedback vectors for a specific card."""
        collection = cls.get_collection()
        
        where_filter = {"card_name": {"$eq": card_name}}
        if feedback_type:
            where_filter = {
                "$and": [
                    {"card_name": {"$eq": card_name}},
                    {"feedback_type": {"$eq": feedback_type}}
                ]
            }
        
        results = collection.get(
            where=where_filter,
            limit=n_results
        )
        
        return results
    
    @classmethod
    def delete_feedback_vector(cls, feedback_id: int) -> bool:
        """Delete a feedback vector from Chroma DB."""
        collection = cls.get_collection()
        vector_id = f"feedback_{feedback_id}"
        
        try:
            collection.delete(ids=[vector_id])
            return True
        except Exception as e:
            print(f"Error deleting vector: {e}")
            return False
    
    @classmethod
    def update_feedback_vector(
        cls,
        feedback_id: int,
        card_name: str,
        feedback_text: str,
        feedback_type: str,
        rating: int,
        user_id: int
    ) -> str:
        """Update a feedback vector in Chroma DB."""
        # Delete the old vector
        cls.delete_feedback_vector(feedback_id)
        
        # Add the new vector
        return cls.add_feedback_vector(
            feedback_id,
            card_name,
            feedback_text,
            feedback_type,
            rating,
            user_id
        )
