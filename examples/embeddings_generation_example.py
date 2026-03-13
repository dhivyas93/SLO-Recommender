"""
Example: Embeddings Generation and Storage

This example demonstrates how to use the RAG engine to:
1. Generate embeddings for knowledge base documents
2. Store embeddings to file
3. Load embeddings for later retrieval

This is typically done during system initialization to pre-compute
embeddings for all knowledge base documents.
"""

import json
import logging
from pathlib import Path
from src.engines.rag_engine import RAGEngine
from src.storage.file_storage import FileStorage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_knowledge_base_embeddings():
    """
    Generate embeddings for all knowledge base documents.
    
    This function:
    1. Loads the RAG engine
    2. Reads knowledge base documents (runbooks, best practices)
    3. Chunks long documents
    4. Generates embeddings for all chunks
    5. Stores embeddings to file
    
    This is typically run once during system initialization.
    """
    
    engine = RAGEngine()
    storage = FileStorage()
    
    # Initialize embeddings structure
    embeddings_data = {
        'runbooks': [],
        'best_practices': [],
        'historical': [],
        'metadata': {
            'model': engine.model_name,
            'embedding_dimension': 384,  # all-MiniLM-L6-v2 produces 384-dim embeddings
            'total_documents': 0
        }
    }
    
    # 1. Generate embeddings for runbooks
    logger.info("Generating embeddings for runbooks...")
    runbooks_dir = Path('data/knowledge/runbooks')
    if runbooks_dir.exists():
        for runbook_file in runbooks_dir.glob('*.md'):
            try:
                # Read runbook content
                content = runbook_file.read_text()
                
                # Chunk the document
                chunks = engine.chunk_document(content, chunk_size=500, overlap=50)
                
                # Generate embeddings for each chunk
                chunk_embeddings = engine.generate_embeddings_batch(chunks)
                
                # Store with metadata
                for chunk, embedding in zip(chunks, chunk_embeddings):
                    embeddings_data['runbooks'].append({
                        'source': str(runbook_file),
                        'content': chunk,
                        'embedding': embedding,
                        'metadata': {
                            'document_type': 'runbook',
                            'filename': runbook_file.name
                        }
                    })
                
                logger.info(f"  ✓ {runbook_file.name}: {len(chunks)} chunks")
            
            except Exception as e:
                logger.error(f"  ✗ Failed to process {runbook_file.name}: {e}")
    
    # 2. Generate embeddings for best practices
    logger.info("Generating embeddings for best practices...")
    best_practices_file = Path('data/knowledge/best_practices/industry-standards.json')
    if best_practices_file.exists():
        try:
            best_practices = storage.read_json(str(best_practices_file))
            
            # Generate embeddings for each practice
            for practice in best_practices:
                # Create a text representation of the practice
                text = f"{practice.get('service_type', 'generic')}: {practice.get('description', '')}"
                embedding = engine.generate_embedding(text)
                
                embeddings_data['best_practices'].append({
                    'source': 'industry-standards',
                    'content': practice,
                    'embedding': embedding,
                    'metadata': {
                        'document_type': 'best_practice',
                        'service_type': practice.get('service_type', 'generic')
                    }
                })
            
            logger.info(f"  ✓ {len(best_practices)} best practices embedded")
        
        except Exception as e:
            logger.error(f"  ✗ Failed to process best practices: {e}")
    
    # 3. Update metadata
    embeddings_data['metadata']['total_documents'] = (
        len(embeddings_data['runbooks']) +
        len(embeddings_data['best_practices']) +
        len(embeddings_data['historical'])
    )
    
    # 4. Store embeddings to file
    embeddings_file = Path('data/knowledge/embeddings/all_embeddings.json')
    embeddings_file.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        engine.store_embeddings(embeddings_data, str(embeddings_file))
        logger.info(f"✓ Embeddings stored to {embeddings_file}")
        logger.info(f"  Total documents embedded: {embeddings_data['metadata']['total_documents']}")
    
    except Exception as e:
        logger.error(f"✗ Failed to store embeddings: {e}")
        raise


def load_and_inspect_embeddings():
    """
    Load embeddings from file and inspect their structure.
    
    This demonstrates how to load pre-computed embeddings for use
    in vector search and retrieval operations.
    """
    
    engine = RAGEngine()
    embeddings_file = Path('data/knowledge/embeddings/all_embeddings.json')
    
    if not embeddings_file.exists():
        logger.warning(f"Embeddings file not found: {embeddings_file}")
        logger.info("Run generate_knowledge_base_embeddings() first")
        return
    
    try:
        # Load embeddings
        embeddings_data = engine.load_embeddings(str(embeddings_file))
        
        # Inspect structure
        logger.info("Embeddings loaded successfully:")
        logger.info(f"  Model: {embeddings_data['metadata']['model']}")
        logger.info(f"  Embedding dimension: {embeddings_data['metadata']['embedding_dimension']}")
        logger.info(f"  Total documents: {embeddings_data['metadata']['total_documents']}")
        logger.info(f"  Runbooks: {len(embeddings_data['runbooks'])} chunks")
        logger.info(f"  Best practices: {len(embeddings_data['best_practices'])} documents")
        logger.info(f"  Historical: {len(embeddings_data['historical'])} documents")
        
        # Show sample embedding
        if embeddings_data['runbooks']:
            sample = embeddings_data['runbooks'][0]
            logger.info(f"\nSample runbook chunk:")
            logger.info(f"  Source: {sample['source']}")
            logger.info(f"  Content preview: {sample['content'][:100]}...")
            logger.info(f"  Embedding shape: {len(sample['embedding'])} dimensions")
    
    except Exception as e:
        logger.error(f"Failed to load embeddings: {e}")
        raise


def generate_single_document_embedding(document_text: str) -> dict:
    """
    Generate embedding for a single document.
    
    This is useful for generating embeddings for new documents
    that are added to the knowledge base after initialization.
    
    Args:
        document_text: The document text to embed
        
    Returns:
        Dictionary with embedding and metadata
    """
    
    engine = RAGEngine()
    
    try:
        # Generate embedding
        embedding = engine.generate_embedding(document_text)
        
        result = {
            'content': document_text,
            'embedding': embedding,
            'metadata': {
                'model': engine.model_name,
                'embedding_dimension': len(embedding)
            }
        }
        
        logger.info(f"✓ Generated embedding for document ({len(embedding)} dimensions)")
        return result
    
    except Exception as e:
        logger.error(f"Failed to generate embedding: {e}")
        raise


def batch_generate_embeddings(documents: list) -> list:
    """
    Generate embeddings for multiple documents efficiently.
    
    Batch processing is more efficient than individual calls.
    
    Args:
        documents: List of document texts
        
    Returns:
        List of dictionaries with embeddings and metadata
    """
    
    engine = RAGEngine()
    
    try:
        # Generate embeddings in batch
        embeddings = engine.generate_embeddings_batch(documents)
        
        results = []
        for doc, embedding in zip(documents, embeddings):
            results.append({
                'content': doc,
                'embedding': embedding,
                'metadata': {
                    'model': engine.model_name,
                    'embedding_dimension': len(embedding)
                }
            })
        
        logger.info(f"✓ Generated {len(results)} embeddings in batch")
        return results
    
    except Exception as e:
        logger.error(f"Failed to generate batch embeddings: {e}")
        raise


if __name__ == '__main__':
    # Example 1: Generate embeddings for entire knowledge base
    logger.info("=" * 60)
    logger.info("Example 1: Generate Knowledge Base Embeddings")
    logger.info("=" * 60)
    try:
        generate_knowledge_base_embeddings()
    except Exception as e:
        logger.error(f"Failed: {e}")
    
    # Example 2: Load and inspect embeddings
    logger.info("\n" + "=" * 60)
    logger.info("Example 2: Load and Inspect Embeddings")
    logger.info("=" * 60)
    try:
        load_and_inspect_embeddings()
    except Exception as e:
        logger.error(f"Failed: {e}")
    
    # Example 3: Generate single document embedding
    logger.info("\n" + "=" * 60)
    logger.info("Example 3: Generate Single Document Embedding")
    logger.info("=" * 60)
    try:
        doc = "API gateways should have 99.9% availability and p95 latency under 200ms"
        result = generate_single_document_embedding(doc)
        logger.info(f"Document: {result['content']}")
        logger.info(f"Embedding dimension: {result['metadata']['embedding_dimension']}")
    except Exception as e:
        logger.error(f"Failed: {e}")
    
    # Example 4: Batch generate embeddings
    logger.info("\n" + "=" * 60)
    logger.info("Example 4: Batch Generate Embeddings")
    logger.info("=" * 60)
    try:
        docs = [
            "Database services should prioritize availability over latency",
            "Message queues need high throughput and low error rates",
            "Cache layers can significantly reduce downstream latency"
        ]
        results = batch_generate_embeddings(docs)
        for i, result in enumerate(results, 1):
            logger.info(f"  Document {i}: {result['content'][:50]}...")
    except Exception as e:
        logger.error(f"Failed: {e}")
