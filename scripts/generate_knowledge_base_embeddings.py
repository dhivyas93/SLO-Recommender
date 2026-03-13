#!/usr/bin/env python3
"""
Generate embeddings for all knowledge base documents.

This script:
1. Loads the RAG engine
2. Reads all knowledge base documents (runbooks, best practices, historical)
3. Chunks long documents
4. Generates embeddings for all chunks
5. Stores embeddings to file

Usage:
    python scripts/generate_knowledge_base_embeddings.py
"""

import json
import logging
from pathlib import Path
from src.engines.rag_engine import RAGEngine
from src.storage.file_storage import FileStorage

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_knowledge_base_embeddings():
    """
    Generate embeddings for all knowledge base documents.
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
            'total_documents': 0,
            'generation_timestamp': str(Path.cwd())
        }
    }
    
    # 1. Generate embeddings for runbooks
    logger.info("=" * 60)
    logger.info("Generating embeddings for runbooks...")
    logger.info("=" * 60)
    
    runbooks_dir = Path('data/knowledge/runbooks')
    if runbooks_dir.exists():
        runbook_files = list(runbooks_dir.glob('*.md'))
        logger.info(f"Found {len(runbook_files)} runbook files")
        
        for runbook_file in runbook_files:
            try:
                # Read runbook content
                content = runbook_file.read_text()
                logger.info(f"\nProcessing: {runbook_file.name}")
                logger.info(f"  Content size: {len(content)} characters")
                
                # Chunk the document
                chunks = engine.chunk_document(content, chunk_size=500, overlap=50)
                logger.info(f"  Chunks: {len(chunks)}")
                
                # Generate embeddings for each chunk
                chunk_embeddings = engine.generate_embeddings_batch(chunks)
                
                # Store with metadata
                for i, (chunk, embedding) in enumerate(zip(chunks, chunk_embeddings)):
                    embeddings_data['runbooks'].append({
                        'source': str(runbook_file),
                        'content': chunk,
                        'embedding': embedding,
                        'metadata': {
                            'document_type': 'runbook',
                            'filename': runbook_file.name,
                            'chunk_index': i,
                            'total_chunks': len(chunks)
                        }
                    })
                
                logger.info(f"  ✓ Generated {len(chunks)} embeddings")
            
            except Exception as e:
                logger.error(f"  ✗ Failed to process {runbook_file.name}: {e}")
    else:
        logger.warning(f"Runbooks directory not found: {runbooks_dir}")
    
    # 2. Generate embeddings for best practices
    logger.info("\n" + "=" * 60)
    logger.info("Generating embeddings for best practices...")
    logger.info("=" * 60)
    
    best_practices_file = Path('data/knowledge/best_practices/industry-standards.json')
    if best_practices_file.exists():
        try:
            best_practices = storage.read_json(str(best_practices_file))
            logger.info(f"Found {len(best_practices)} best practices")
            
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
            
            logger.info(f"✓ Generated {len(best_practices)} embeddings")
        
        except Exception as e:
            logger.error(f"✗ Failed to process best practices: {e}")
    else:
        logger.warning(f"Best practices file not found: {best_practices_file}")
    
    # 3. Generate embeddings for historical patterns
    logger.info("\n" + "=" * 60)
    logger.info("Generating embeddings for historical patterns...")
    logger.info("=" * 60)
    
    historical_dir = Path('data/knowledge/historical')
    if historical_dir.exists():
        historical_files = list(historical_dir.glob('*.json'))
        logger.info(f"Found {len(historical_files)} historical files")
        
        for historical_file in historical_files:
            try:
                logger.info(f"\nProcessing: {historical_file.name}")
                
                # Read historical data
                historical_data = storage.read_json(str(historical_file))
                
                # Handle both list and dict formats
                if isinstance(historical_data, list):
                    items = historical_data
                else:
                    items = [historical_data]
                
                logger.info(f"  Items: {len(items)}")
                
                # Generate embeddings for each item
                for item in items:
                    # Create a text representation
                    if isinstance(item, dict):
                        text = json.dumps(item, indent=2)[:500]  # Limit to 500 chars
                    else:
                        text = str(item)[:500]
                    
                    embedding = engine.generate_embedding(text)
                    
                    embeddings_data['historical'].append({
                        'source': str(historical_file),
                        'content': item,
                        'embedding': embedding,
                        'metadata': {
                            'document_type': 'historical',
                            'filename': historical_file.name
                        }
                    })
                
                logger.info(f"  ✓ Generated {len(items)} embeddings")
            
            except Exception as e:
                logger.error(f"  ✗ Failed to process {historical_file.name}: {e}")
    else:
        logger.warning(f"Historical directory not found: {historical_dir}")
    
    # 4. Update metadata
    embeddings_data['metadata']['total_documents'] = (
        len(embeddings_data['runbooks']) +
        len(embeddings_data['best_practices']) +
        len(embeddings_data['historical'])
    )
    
    # 5. Store embeddings to file
    logger.info("\n" + "=" * 60)
    logger.info("Storing embeddings to file...")
    logger.info("=" * 60)
    
    embeddings_file = Path('data/knowledge/embeddings/all_embeddings.json')
    embeddings_file.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        engine.store_embeddings(embeddings_data, str(embeddings_file))
        logger.info(f"✓ Embeddings stored to {embeddings_file}")
        logger.info(f"  Total documents embedded: {embeddings_data['metadata']['total_documents']}")
        logger.info(f"  Runbooks: {len(embeddings_data['runbooks'])} chunks")
        logger.info(f"  Best practices: {len(embeddings_data['best_practices'])} documents")
        logger.info(f"  Historical: {len(embeddings_data['historical'])} documents")
        logger.info(f"  Embedding dimension: {embeddings_data['metadata']['embedding_dimension']}")
    
    except Exception as e:
        logger.error(f"✗ Failed to store embeddings: {e}")
        raise
    
    logger.info("\n" + "=" * 60)
    logger.info("✓ Knowledge base embeddings generated successfully!")
    logger.info("=" * 60)


if __name__ == '__main__':
    try:
        generate_knowledge_base_embeddings()
    except Exception as e:
        logger.error(f"Failed to generate embeddings: {e}")
        exit(1)
