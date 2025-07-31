import os
import asyncio
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import mimetypes
from dataclasses import dataclass
from datetime import datetime, timezone

try:
    from langchain_community.document_loaders import (
        PyMuPDFLoader, 
        TextLoader, 
        UnstructuredCSVLoader, 
        UnstructuredExcelLoader,
        UnstructuredMarkdownLoader, 
        UnstructuredPowerPointLoader,
        UnstructuredWordDocumentLoader
    )
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_openai import OpenAIEmbeddings
    from langchain_chroma import Chroma
    from langchain_community.vectorstores.utils import filter_complex_metadata
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

from src.tools import AsyncTool, ToolResult
from src.registry import TOOL
from src.logger import logger
from src.utils import assemble_project_path

@dataclass
class DocumentMetadata:
    """Comprehensive metadata for indexed documents"""
    # File identification
    file_path: str
    file_name: str
    file_directory: str
    relative_path: str
    
    # File properties
    file_size: int
    file_type: str
    mime_type: str
    file_extension: str
    
    # Timestamps
    created_at: str
    modified_at: str
    accessed_at: str
    indexed_at: str
    
    # Content properties  
    chunk_count: int
    total_characters: int
    file_hash: str
    
    # System properties
    file_permissions: str
    is_hidden: bool
    is_symlink: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary for storage"""
        return {
            'file_path': self.file_path,
            'file_name': self.file_name,
            'file_directory': self.file_directory,
            'relative_path': self.relative_path,
            'file_size': self.file_size,
            'file_type': self.file_type,
            'mime_type': self.mime_type,
            'file_extension': self.file_extension,
            'created_at': self.created_at,
            'modified_at': self.modified_at,
            'accessed_at': self.accessed_at,
            'indexed_at': self.indexed_at,
            'chunk_count': self.chunk_count,
            'total_characters': self.total_characters,
            'file_hash': self.file_hash,
            'file_permissions': self.file_permissions,
            'is_hidden': self.is_hidden,
            'is_symlink': self.is_symlink
        }
    
    @classmethod
    def from_file_path(cls, file_path: str, base_directory: str = None) -> 'DocumentMetadata':
        """Create comprehensive metadata from file path"""
        path_obj = Path(file_path)
        stat_info = path_obj.stat()
        
        # Get relative path if base directory provided
        if base_directory:
            try:
                relative_path = str(path_obj.relative_to(Path(base_directory)))
            except ValueError:
                relative_path = str(path_obj)
        else:
            relative_path = str(path_obj)
        
        # Get MIME type
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = 'application/octet-stream'
        
        # Get timestamps
        created_at = datetime.fromtimestamp(stat_info.st_ctime, tz=timezone.utc).isoformat()
        modified_at = datetime.fromtimestamp(stat_info.st_mtime, tz=timezone.utc).isoformat()
        accessed_at = datetime.fromtimestamp(stat_info.st_atime, tz=timezone.utc).isoformat()
        indexed_at = datetime.now(tz=timezone.utc).isoformat()
        
        # Get file permissions
        permissions = oct(stat_info.st_mode)[-3:]
        
        return cls(
            file_path=str(path_obj.absolute()),
            file_name=path_obj.name,
            file_directory=str(path_obj.parent),
            relative_path=relative_path,
            file_size=stat_info.st_size,
            file_type=path_obj.suffix.lower() if path_obj.suffix else 'no_extension',
            mime_type=mime_type,
            file_extension=path_obj.suffix.lower(),
            created_at=created_at,
            modified_at=modified_at,
            accessed_at=accessed_at,
            indexed_at=indexed_at,
            chunk_count=0,  # Will be updated later
            total_characters=0,  # Will be updated later
            file_hash='',  # Will be calculated later
            file_permissions=permissions,
            is_hidden=path_obj.name.startswith('.'),
            is_symlink=path_obj.is_symlink()
        )

class VectorDatabaseManager:
    """Manages vector database operations with optimizations and error handling"""
    
    def __init__(self, 
                 db_path: str = "vector_db",
                 chunk_size: int = 1000,
                 chunk_overlap: int = 200,
                 embeddings_model: str = "text-embedding-3-small"):
        
        if not LANGCHAIN_AVAILABLE:
            raise ImportError(
                "LangChain dependencies not available. Please install: "
                "pip install langchain langchain-community langchain-openai langchain-chroma"
            )
        
        # Check for additional dependencies
        self._check_optional_dependencies()
        
        self.db_path = assemble_project_path(db_path)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.embeddings_model = embeddings_model
        
        # Initialize components
        self.embeddings = OpenAIEmbeddings(model=embeddings_model)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " ", ""]
        )
        
        # Supported file types and their loaders
        self.file_loaders = {
            '.pdf': PyMuPDFLoader,
            '.txt': TextLoader,
            '.md': UnstructuredMarkdownLoader,
            '.csv': UnstructuredCSVLoader,
            '.xlsx': UnstructuredExcelLoader,
            '.xls': UnstructuredExcelLoader,
            '.pptx': UnstructuredPowerPointLoader,
            '.docx': UnstructuredWordDocumentLoader,
            '.py': TextLoader,
            '.js': TextLoader,
            '.ts': TextLoader,
            '.html': TextLoader,
            '.css': TextLoader,
            '.json': TextLoader,
            '.xml': TextLoader,
            '.yaml': TextLoader,
            '.yml': TextLoader,
        }
        
        # Metadata storage
        self.metadata_file = os.path.join(self.db_path, "metadata.json")
        self.vectorstore = None
    
    def _check_optional_dependencies(self):
        """Check for optional dependencies and warn if missing"""
        optional_deps = {
            'msoffcrypto': 'msoffcrypto-tool (for encrypted Office files)',
            'unstructured': 'unstructured (for document processing)',
            'pymupdf': 'pymupdf (for PDF processing)',
            'python_docx': 'python-docx (for Word documents)',
            'openpyxl': 'openpyxl (for Excel files)',
        }
        
        missing_deps = []
        for module, description in optional_deps.items():
            try:
                __import__(module)
            except ImportError:
                missing_deps.append(description)
        
        if missing_deps:
            from src.utils.debug_config import is_debug_mode
            if is_debug_mode():
                logger.warning("Some optional dependencies are missing:")
                for dep in missing_deps:
                    logger.warning(f"  - {dep}")
    
    def _estimate_tokens(self, text: str) -> int:
        """More accurate token estimation for OpenAI models"""
        if not text:
            return 0
        
        # More accurate estimation based on OpenAI's tokenization patterns
        # Account for:
        # - Average word length in English is ~4.7 characters
        # - Tokens per word varies but averages ~1.3 tokens per word
        # - Punctuation and spaces add tokens
        # - Metadata overhead
        
        # Rough but more accurate estimate: 1 token ≈ 3.2 characters
        base_tokens = len(text) // 3
        
        # Add metadata overhead (estimate ~50-100 tokens per chunk for our metadata)
        metadata_overhead = 75
        
        return base_tokens + metadata_overhead
    
    def _calculate_adaptive_batch_size(self, chunks, max_tokens: int = 250000) -> int:
        """Calculate adaptive batch size with conservative token estimation"""
        if not chunks:
            return 50  # Conservative default
        
        # Sample more chunks for better estimation (up to 50 chunks)
        sample_size = min(50, len(chunks))
        sample_chunks = chunks[:sample_size]
        
        # Calculate token estimates for sample
        token_estimates = []
        for chunk in sample_chunks:
            content_tokens = self._estimate_tokens(chunk.page_content)
            # Add estimated metadata tokens (our metadata can be substantial)
            metadata_size = sum(len(str(v)) for v in chunk.metadata.values()) if hasattr(chunk, 'metadata') else 0
            metadata_tokens = metadata_size // 3
            total_tokens = content_tokens + metadata_tokens
            token_estimates.append(total_tokens)
        
        if not token_estimates:
            return 50
        
        # Use statistical analysis for better estimation
        avg_tokens = sum(token_estimates) / len(token_estimates)
        max_tokens_in_sample = max(token_estimates)
        
        # Use the higher of average or 80th percentile for safety
        sorted_estimates = sorted(token_estimates)
        percentile_80 = sorted_estimates[int(len(sorted_estimates) * 0.8)]
        conservative_tokens_per_chunk = max(avg_tokens, percentile_80)
        
        # Very conservative safety margin (60% of max tokens)
        safe_max_tokens = int(max_tokens * 0.6)
        
        # Calculate initial batch size
        batch_size = max(1, int(safe_max_tokens / conservative_tokens_per_chunk))
        
        # Apply intelligent limits based on content analysis
        if max_tokens_in_sample > avg_tokens * 2:
            # High variance in chunk sizes - use smaller batches
            batch_size = min(batch_size, 200)
        else:
            # More consistent chunk sizes
            batch_size = min(batch_size, 500)
        
        # Hard limits
        batch_size = max(batch_size, 5)    # Absolute minimum
        batch_size = min(batch_size, 800)  # Absolute maximum
        
        logger.info(f"Adaptive batch size: {batch_size} chunks")
        logger.info(f"  • Avg tokens per chunk: {avg_tokens:.0f}")
        logger.info(f"  • Max tokens in sample: {max_tokens_in_sample:.0f}")
        logger.info(f"  • Conservative estimate: {conservative_tokens_per_chunk:.0f}")
        
        return batch_size
    
    def _split_batch_intelligently(self, batch_chunks, target_token_limit: int = 250000):
        """Intelligently split a batch based on actual token content"""
        if len(batch_chunks) <= 1:
            return [batch_chunks] if batch_chunks else []
        
        # Calculate actual tokens for each chunk in this batch
        chunk_tokens = []
        for chunk in batch_chunks:
            content_tokens = self._estimate_tokens(chunk.page_content)
            metadata_size = sum(len(str(v)) for v in chunk.metadata.values()) if hasattr(chunk, 'metadata') else 0
            metadata_tokens = metadata_size // 3
            total_tokens = content_tokens + metadata_tokens
            chunk_tokens.append(total_tokens)
        
        # Find optimal split points
        batches = []
        current_batch = []
        current_tokens = 0
        safe_limit = int(target_token_limit * 0.5)  # Very conservative for problematic batches
        
        for i, (chunk, tokens) in enumerate(zip(batch_chunks, chunk_tokens)):
            # If adding this chunk would exceed limit, start new batch
            if current_tokens + tokens > safe_limit and current_batch:
                batches.append(current_batch)
                current_batch = [chunk]
                current_tokens = tokens
            else:
                current_batch.append(chunk)
                current_tokens += tokens
        
        # Add remaining chunks
        if current_batch:
            batches.append(current_batch)
        
        logger.info(f"Split batch of {len(batch_chunks)} chunks into {len(batches)} sub-batches")
        for i, sub_batch in enumerate(batches):
            est_tokens = sum(chunk_tokens[batch_chunks.index(chunk)] for chunk in sub_batch if chunk in batch_chunks)
            logger.info(f"  Sub-batch {i+1}: {len(sub_batch)} chunks (~{est_tokens} tokens)")
        
        return batches
    
    def _filter_document_metadata(self, documents):
        """Filter complex metadata from documents to ensure ChromaDB compatibility"""
        if not LANGCHAIN_AVAILABLE:
            return documents
        
        logger.info(f"Filtering complex metadata from {len(documents)} documents...")
        
        try:
            # Use langchain's built-in filter for complex metadata
            filtered_documents = filter_complex_metadata(documents)
            logger.info(f"Successfully filtered metadata for {len(documents)} documents using langchain filter")
            return filtered_documents
        except Exception as e:
            logger.warning(f"Langchain metadata filter failed: {e}")
            logger.info("Applying manual metadata filtering...")
            
            # Fallback: manually filter out complex metadata types
            problematic_keys = set()
            for doc_idx, doc in enumerate(documents):
                if hasattr(doc, 'metadata') and doc.metadata:
                    filtered_metadata = {}
                    for key, value in doc.metadata.items():
                        # Keep only simple types that ChromaDB accepts
                        if isinstance(value, (str, int, float, bool, type(None))):
                            filtered_metadata[key] = value
                        elif isinstance(value, (list, dict, tuple, set)):
                            # Convert complex types to strings
                            problematic_keys.add(f"{key}({type(value).__name__})")
                            filtered_metadata[key] = str(value)
                        else:
                            # Convert other types to string representation
                            problematic_keys.add(f"{key}({type(value).__name__})")
                            filtered_metadata[key] = str(value)
                    doc.metadata = filtered_metadata
            
            if problematic_keys:
                logger.info(f"Converted {len(problematic_keys)} complex metadata types to strings: {', '.join(sorted(problematic_keys))}")
            
            return documents

    def _process_chunks_in_batches(self, document_chunks) -> Dict[str, Any]:
        """Process document chunks in batches with intelligent splitting and error recovery"""
        if not document_chunks:
            return {'success': True, 'batches_processed': 0}

        # Filter complex metadata from all documents before processing
        logger.info("Filtering complex metadata from documents...")
        document_chunks = self._filter_document_metadata(document_chunks)
        
        # Calculate optimal batch size
        batch_size = self._calculate_adaptive_batch_size(document_chunks)
        total_chunks = len(document_chunks)
        total_batches = (total_chunks + batch_size - 1) // batch_size
        
        logger.info(f"Processing {total_chunks} chunks using adaptive batching")
        logger.info(f"Initial plan: {total_batches} batches of ~{batch_size} chunks each")
        
        try:
            # Check if vectorstore exists
            vectorstore_exists = os.path.exists(self.db_path) and any(os.listdir(self.db_path))
            
            # Initialize vectorstore for first batch
            if not vectorstore_exists:
                logger.info("Creating new vector database...")
                first_batch = document_chunks[:batch_size]
                
                # Try creating vectorstore with adaptive first batch
                success = self._process_single_batch_with_splitting(first_batch, "initial")
                if not success:
                    return {
                        'success': False,
                        'error': 'Failed to create initial vector database',
                        'batches_processed': 0
                    }
                
                logger.info(f"Created vectorstore with initial batch")
                remaining_chunks = document_chunks[batch_size:]
                start_idx = batch_size
            else:
                logger.info("Loading existing vector database...")
                # Load existing vectorstore
                self.vectorstore = Chroma(
                    persist_directory=self.db_path,
                    embedding_function=self.embeddings
                )
                remaining_chunks = document_chunks
                start_idx = 0
            
            # Process remaining chunks with intelligent batching
            batches_processed = 1 if not vectorstore_exists else 0
            chunks_processed = batch_size if not vectorstore_exists else 0
            
            while chunks_processed < total_chunks:
                # Calculate dynamic batch size for remaining chunks
                remaining_count = total_chunks - chunks_processed
                current_batch_size = min(batch_size, remaining_count)
                
                # Get current batch
                current_batch = document_chunks[chunks_processed:chunks_processed + current_batch_size]
                
                if not current_batch:
                    break
                
                batch_number = batches_processed + 1
                logger.info(f"Processing batch {batch_number}: {len(current_batch)} chunks")
                logger.info(f"Progress: {chunks_processed + len(current_batch)}/{total_chunks} chunks ({((chunks_processed + len(current_batch)) / total_chunks * 100):.1f}%)")
                
                # Process batch with intelligent splitting
                success = self._process_single_batch_with_splitting(current_batch, f"batch_{batch_number}")
                
                if success:
                    batches_processed += 1
                    chunks_processed += len(current_batch)
                    
                    # Log progress every 10 batches or at major milestones
                    if batch_number % 10 == 0 or chunks_processed >= total_chunks:
                        progress_pct = (chunks_processed / total_chunks) * 100
                        logger.info(f"Batch processing progress: {chunks_processed}/{total_chunks} chunks ({progress_pct:.1f}%)")
                else:
                    # Failed to process batch even with splitting
                    return {
                        'success': False,
                        'error': f'Failed to process batch {batch_number} after all attempts',
                        'batches_processed': batches_processed,
                        'chunks_processed': chunks_processed
                    }
            
            logger.info(f"Successfully processed all {total_chunks} chunks in {batches_processed} batches")
            
            return {
                'success': True,
                'batches_processed': batches_processed,
                'chunks_processed': chunks_processed
            }
            
        except Exception as e:
            logger.error(f"Error in batch processing: {e}")
            return {
                'success': False,
                'error': str(e),
                'batches_processed': batches_processed if 'batches_processed' in locals() else 0
            }
    
    def _process_single_batch_with_splitting(self, batch_chunks, batch_name: str) -> bool:
        """Process a single batch with intelligent splitting if needed"""
        max_attempts = 5
        attempt = 1
        
        while attempt <= max_attempts:
            try:
                if not hasattr(self, 'vectorstore') or self.vectorstore is None:
                    # Create new vectorstore
                    self.vectorstore = Chroma.from_documents(
                        documents=batch_chunks,
                        embedding=self.embeddings,
                        persist_directory=self.db_path
                    )
                else:
                    # Add to existing vectorstore
                    self.vectorstore.add_documents(batch_chunks)
                
                logger.debug(f"Successfully processed {batch_name} with {len(batch_chunks)} chunks")
                return True
                
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"Attempt {attempt}/{max_attempts} failed for {batch_name}: {error_msg}")
                
                # Handle metadata errors
                if "Expected metadata value to be" in error_msg:
                    logger.info(f"Applying additional metadata filtering to {batch_name}...")
                    batch_chunks = self._filter_document_metadata(batch_chunks)
                    attempt += 1
                    continue
                
                # Handle token limit errors with intelligent splitting
                if "max_tokens_per_request" in error_msg:
                    if len(batch_chunks) <= 1:
                        logger.error(f"Cannot split {batch_name} further - single chunk exceeds token limit")
                        return False
                    
                    logger.info(f"Token limit exceeded for {batch_name}, applying intelligent splitting...")
                    
                    # Use intelligent splitting
                    sub_batches = self._split_batch_intelligently(batch_chunks)
                    
                    if not sub_batches:
                        logger.error(f"Intelligent splitting failed for {batch_name}")
                        return False
                    
                    # Process each sub-batch
                    success_count = 0
                    for i, sub_batch in enumerate(sub_batches):
                        sub_batch_name = f"{batch_name}_split_{i+1}"
                        if self._process_single_batch_with_splitting(sub_batch, sub_batch_name):
                            success_count += 1
                        else:
                            logger.error(f"Failed to process {sub_batch_name}")
                            return False
                    
                    logger.info(f"Successfully processed {batch_name} using {len(sub_batches)} sub-batches")
                    return True
                
                # Other errors - retry with exponential backoff
                if attempt < max_attempts:
                    wait_time = min(2 ** attempt, 10)  # Cap at 10 seconds
                    logger.info(f"Retrying {batch_name} in {wait_time} seconds...")
                    time.sleep(wait_time)
                
                attempt += 1
        
        logger.error(f"Failed to process {batch_name} after {max_attempts} attempts")
        return False
    
    def _get_file_hash(self, file_path: str) -> str:
        """Generate MD5 hash of file for change detection"""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.warning(f"Could not hash file {file_path}: {e}")
            return ""
    
    def _load_metadata(self) -> Dict[str, DocumentMetadata]:
        """Load existing metadata from disk"""
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, 'r') as f:
                    data = json.load(f)
                    return {
                        path: DocumentMetadata(**meta) 
                        for path, meta in data.items()
                    }
            except Exception as e:
                logger.warning(f"Could not load metadata: {e}")
        return {}
    
    def _save_metadata(self, metadata: Dict[str, DocumentMetadata]):
        """Save comprehensive metadata to disk"""
        os.makedirs(os.path.dirname(self.metadata_file), exist_ok=True)
        try:
            # Convert DocumentMetadata objects to dictionaries using to_dict() method
            serializable_metadata = {}
            for path, meta in metadata.items():
                if hasattr(meta, 'to_dict'):
                    serializable_metadata[path] = meta.to_dict()
                else:
                    # Fallback for backward compatibility
                    serializable_metadata[path] = meta.__dict__ if hasattr(meta, '__dict__') else str(meta)
                    
            with open(self.metadata_file, 'w') as f:
                json.dump(serializable_metadata, f, indent=2, default=str)
                
            logger.info(f"Saved metadata for {len(metadata)} files to {self.metadata_file}")
        except Exception as e:
            logger.error(f"Could not save metadata: {e}")
            logger.error(f"Metadata file path: {self.metadata_file}")
    
    def _scan_directory(self, directory: str) -> List[str]:
        """Recursively scan directory for supported files"""
        supported_files = []
        directory_path = Path(directory)
        
        if not directory_path.exists():
            raise ValueError(f"Directory does not exist: {directory}")
        
        for file_path in directory_path.rglob("*"):
            if file_path.is_file():
                file_ext = file_path.suffix.lower()
                if file_ext in self.file_loaders:
                    supported_files.append(str(file_path))
        
        return supported_files
    
    def _load_single_document(self, file_path: str) -> List[Any]:
        """Load a single document using appropriate loader with comprehensive metadata"""
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext not in self.file_loaders:
            raise ValueError(f"Unsupported file type: {file_ext}")
        
        loader_class = self.file_loaders[file_ext]
        
        try:
            # Handle different loader requirements
            if file_ext in ['.txt', '.py', '.js', '.ts', '.html', '.css', '.json', '.xml', '.yaml', '.yml']:
                loader = loader_class(file_path, encoding='utf-8')
            elif file_ext in ['.xlsx', '.xls']:
                # For Excel files, try with mode parameter to handle encrypted files
                try:
                    loader = loader_class(file_path, mode="elements")
                except Exception:
                    # Fallback for older versions or different configurations
                    loader = loader_class(file_path)
            elif file_ext == '.pptx':
                # For PowerPoint files
                try:
                    loader = loader_class(file_path, mode="elements")
                except Exception:
                    loader = loader_class(file_path)
            elif file_ext == '.docx':
                # For Word documents
                try:
                    loader = loader_class(file_path, mode="elements")
                except Exception:
                    loader = loader_class(file_path)
            elif file_ext == '.csv':
                # For CSV files
                try:
                    loader = loader_class(file_path, mode="elements")
                except Exception:
                    loader = loader_class(file_path)
            else:
                loader = loader_class(file_path)
            
            documents = loader.load()
            
            # Create comprehensive metadata for this file
            file_metadata = DocumentMetadata.from_file_path(file_path, base_directory=getattr(self, '_current_index_directory', None))
            
            # Calculate total characters across all document chunks
            total_characters = sum(len(doc.page_content) for doc in documents)
            file_metadata.total_characters = total_characters
            file_metadata.chunk_count = len(documents)
            file_metadata.file_hash = self._get_file_hash(file_path)
            
            # Add comprehensive metadata to each document chunk
            for i, doc in enumerate(documents):
                # Convert metadata to dict for langchain compatibility
                metadata_dict = file_metadata.to_dict()
                
                # Add chunk-specific information (ensure all values are simple types)
                chunk_metadata = {
                    'chunk_index': int(i),
                    'chunk_id': str(f"{file_metadata.file_hash}_{i}"),
                    'content_length': int(len(doc.page_content)),
                    'content_preview': str(doc.page_content[:200] + '...' if len(doc.page_content) > 200 else doc.page_content),
                    
                    # Legacy field names for backward compatibility
                    'source_file': str(file_path),
                    'file_type': str(file_ext),
                    'file_size': int(file_metadata.file_size)
                }
                
                # Ensure all metadata values are simple types
                safe_metadata_dict = {}
                for key, value in metadata_dict.items():
                    if isinstance(value, (str, int, float, bool, type(None))):
                        safe_metadata_dict[key] = value
                    else:
                        # Convert complex types to strings
                        safe_metadata_dict[key] = str(value)
                
                # Add chunk-specific metadata
                safe_metadata_dict.update(chunk_metadata)
                
                # Update document metadata with safe values
                doc.metadata.update(safe_metadata_dict)
            
            return documents
            
        except ImportError as e:
            logger.warning(f"Missing dependency for {file_path}: {e}")
            logger.warning(f"Please install required dependencies. See requirements.txt for details.")
            return []
        except Exception as e:
            logger.warning(f"Failed to load {file_path}: {e}")
            # For encrypted files, provide specific guidance
            if "encrypted" in str(e).lower() or "password" in str(e).lower():
                logger.warning(f"File appears to be password-protected: {file_path}")
                logger.warning("Please remove password protection or provide an unencrypted version.")
            return []
    
    async def index_directory(self, directory: str, progress_callback=None) -> Dict[str, Any]:
        """Index all supported documents in a directory"""
        logger.info(f"Starting indexing of directory: {directory}")
        
        # Store the base directory for relative path calculation
        self._current_index_directory = directory
        
        # Scan for files
        files = self._scan_directory(directory)
        logger.info(f"Found {len(files)} supported files")
        
        if not files:
            return {
                'status': 'completed',
                'message': 'No supported files found in directory',
                'files_processed': 0,
                'documents_indexed': 0
            }
        
        # Load existing metadata
        metadata = self._load_metadata()
        
        # Determine which files need processing
        files_to_process = []
        for file_path in files:
            file_hash = self._get_file_hash(file_path)
            
            if (file_path not in metadata or 
                metadata[file_path].file_hash != file_hash):
                files_to_process.append(file_path)
        
        if not files_to_process:
            logger.info("All files are up to date")
            return {
                'status': 'completed',
                'message': 'All files are already indexed and up to date',
                'files_processed': 0,
                'documents_indexed': len(files)
            }
        
        logger.info(f"Processing {len(files_to_process)} new/changed files")
        
        # Load documents in parallel
        all_documents = []
        processed_count = 0
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            # Submit all loading tasks
            future_to_file = {
                executor.submit(self._load_single_document, file_path): file_path 
                for file_path in files_to_process
            }
            
            for future in future_to_file:
                file_path = future_to_file[future]
                try:
                    documents = future.result()
                    if documents:
                        all_documents.extend(documents)
                        
                        # Update metadata
                        metadata[file_path] = DocumentMetadata.from_file_path(file_path, base_directory=getattr(self, '_current_index_directory', None))
                    
                    processed_count += 1
                    if progress_callback:
                        progress_callback(processed_count, len(files_to_process))
                        
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {e}")
        
        if not all_documents:
            return {
                'status': 'error',
                'message': 'No documents could be loaded',
                'files_processed': processed_count,
                'documents_indexed': 0
            }
        
        # Split documents into chunks
        logger.info(f"Splitting {len(all_documents)} documents into chunks")
        document_chunks = self.text_splitter.split_documents(all_documents)
        logger.info(f"Created {len(document_chunks)} chunks")
        
        # Initialize or update vector store with intelligent batch processing
        try:
            # Process chunks in batches with intelligent splitting and error recovery
            batch_results = self._process_chunks_in_batches(document_chunks)
            
            if not batch_results['success']:
                # Provide detailed error information
                error_msg = batch_results.get('error', 'Unknown batch processing error')
                batches_completed = batch_results.get('batches_processed', 0)
                chunks_completed = batch_results.get('chunks_processed', 0)
                
                logger.error(f"Batch processing failed after {batches_completed} batches ({chunks_completed}/{len(document_chunks)} chunks)")
                logger.error(f"Error details: {error_msg}")
                
                # Save metadata for successfully processed files
                if chunks_completed > 0:
                    logger.info(f"Saving metadata for {processed_count} files (partial indexing)")
                    self._save_metadata(metadata)
                
                return {
                    'status': 'partial' if chunks_completed > 0 else 'error',
                    'message': f'Indexing failed: {error_msg}',
                    'files_processed': processed_count,
                    'documents_indexed': chunks_completed,
                    'total_chunks': len(document_chunks),
                    'batches_completed': batches_completed,
                    'error_details': error_msg
                }
            
            # Save metadata for all files
            self._save_metadata(metadata)
            
            # Success message with detailed statistics
            batches_used = batch_results['batches_processed']
            chunks_processed = batch_results.get('chunks_processed', len(document_chunks))
            
            logger.info(f"✅ Successfully indexed {len(document_chunks)} document chunks")
            logger.info(f"   • Files processed: {len(files_to_process)}")
            logger.info(f"   • Documents loaded: {len(all_documents)}")
            logger.info(f"   • Chunks created: {len(document_chunks)}")
            logger.info(f"   • Batches used: {batches_used}")
            logger.info(f"   • Database path: {self.db_path}")
            
            return {
                'status': 'completed',
                'message': f'Successfully indexed {len(files_to_process)} files into {len(document_chunks)} chunks using {batches_used} adaptive batches',
                'files_processed': processed_count,
                'documents_indexed': len(document_chunks),
                'total_chunks': len(document_chunks),
                'db_path': self.db_path,
                'batches_processed': batches_used,
                'adaptive_batching': True
            }
            
        except Exception as e:
            logger.error(f"Error in vector store operations: {e}")
            logger.error(f"This may be due to API limits, network issues, or corrupted data")
            
            # Try to save metadata even if vector store creation failed
            try:
                self._save_metadata(metadata)
                logger.info("Metadata saved despite vector store error")
            except Exception as meta_error:
                logger.error(f"Could not save metadata: {meta_error}")
            
            return {
                'status': 'error',
                'message': f'Vector store error: {str(e)}',
                'files_processed': processed_count,
                'documents_indexed': 0,
                'error_details': str(e),
                'recovery_suggestion': 'Try reducing the number of files or check API limits'
            }
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Convert file size to human readable format"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        import math
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_names[i]}"
    
    def _format_timestamp(self, iso_timestamp: str) -> str:
        """Convert ISO timestamp to readable format"""
        try:
            dt = datetime.fromisoformat(iso_timestamp.replace('Z', '+00:00'))
            return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        except:
            return iso_timestamp
    
    def _format_metadata_for_display(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Format metadata for beautiful display in search results"""
        
        formatted = {
            # File Information
            'file_info': {
                'name': metadata.get('file_name', 'Unknown'),
                'path': metadata.get('relative_path', metadata.get('source_file', 'Unknown')),
                'directory': metadata.get('file_directory', 'Unknown'),
                'type': metadata.get('file_type', metadata.get('file_extension', 'Unknown')),
                'mime_type': metadata.get('mime_type', 'Unknown'),
                'size': self._format_file_size(metadata.get('file_size', 0)),
                'size_bytes': metadata.get('file_size', 0)
            },
            
            # Timestamps
            'timestamps': {
                'created': self._format_timestamp(metadata.get('created_at', 'Unknown')),
                'modified': self._format_timestamp(metadata.get('modified_at', 'Unknown')),
                'accessed': self._format_timestamp(metadata.get('accessed_at', 'Unknown')),
                'indexed': self._format_timestamp(metadata.get('indexed_at', 'Unknown'))
            },
            
            # Content Information
            'content_info': {
                'chunk_index': metadata.get('chunk_index', 0),
                'chunk_id': metadata.get('chunk_id', 'Unknown'),
                'chunk_length': metadata.get('content_length', 0),
                'total_file_characters': metadata.get('total_characters', 0),
                'total_file_chunks': metadata.get('chunk_count', 0),
                'preview': metadata.get('content_preview', 'No preview available')
            },
            
            # System Information
            'system_info': {
                'permissions': metadata.get('file_permissions', 'Unknown'),
                'is_hidden': metadata.get('is_hidden', False),
                'is_symlink': metadata.get('is_symlink', False),
                'file_hash': metadata.get('file_hash', 'Unknown')
            }
        }
        
        return formatted

    def search_documents(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search indexed documents with comprehensive metadata"""
        if not self.vectorstore:
            # Try to load existing vectorstore
            if os.path.exists(self.db_path):
                try:
                    self.vectorstore = Chroma(
                        persist_directory=self.db_path,
                        embedding_function=self.embeddings
                    )
                except Exception as e:
                    raise ValueError(f"Could not load vector database: {e}")
            else:
                raise ValueError("No vector database found. Please index documents first.")
        
        try:
            results = self.vectorstore.similarity_search_with_score(query, k=k)
            
            formatted_results = []
            for i, (doc, score) in enumerate(results):
                
                # Format comprehensive metadata for display
                formatted_metadata = self._format_metadata_for_display(doc.metadata)
                
                # Create enhanced result
                result = {
                    'rank': i + 1,
                    'similarity_score': score,
                    'content': doc.page_content,
                    'full_content': doc.page_content,  # For backward compatibility
                    'content_preview': doc.page_content[:300] + '...' if len(doc.page_content) > 300 else doc.page_content,
                    
                    # Formatted metadata sections
                    'file_info': formatted_metadata['file_info'],
                    'timestamps': formatted_metadata['timestamps'], 
                    'content_info': formatted_metadata['content_info'],
                    'system_info': formatted_metadata['system_info'],
                    
                    # Raw metadata for programmatic access
                    'raw_metadata': doc.metadata,
                    
                    # Legacy fields for backward compatibility
                    'source_file': doc.metadata.get('source_file', 'Unknown'),
                    'file_type': doc.metadata.get('file_type', 'Unknown'),
                    'file_size': doc.metadata.get('file_size', 0),
                    'metadata': doc.metadata
                }
                
                formatted_results.append(result)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return []

@TOOL.register_module(name="vector_indexer_tool", force=True)
class VectorIndexerTool(AsyncTool):
    """Tool for indexing documents into a vector database"""
    
    name = "vector_indexer_tool"
    description = "Index documents from a directory into a vector database for semantic search and retrieval."
    parameters = {
        "type": "object",
        "properties": {
            "directory_path": {
                "type": "string",
                "description": "Path to the directory containing documents to index"
            },
            "force_reindex": {
                "type": "boolean",
                "description": "Whether to force re-indexing of all documents (default: False)",
                "default": False,
                "nullable": True
            }
        },
        "required": ["directory_path"]
    }
    output_type = "any"
    
    def __init__(self, 
                 db_path: str = "vector_db",
                 chunk_size: int = 1000,
                 chunk_overlap: int = 200,
                 embeddings_model: str = "text-embedding-3-small",
                 **kwargs):
        super().__init__()
        # Ignore any extra kwargs like 'name' from configuration
        
        self.db_manager = VectorDatabaseManager(
            db_path=db_path,
            chunk_size=chunk_size, 
            chunk_overlap=chunk_overlap,
            embeddings_model=embeddings_model
        )
    
    async def forward(self, directory_path: str, force_reindex: bool = False) -> ToolResult:
        """Index documents from the specified directory"""
        try:
            # Validate directory path
            if not os.path.exists(directory_path):
                return ToolResult(
                    output=None,
                    error=f"Directory does not exist: {directory_path}"
                )
            
            if not os.path.isdir(directory_path):
                return ToolResult(
                    output=None,
                    error=f"Path is not a directory: {directory_path}"
                )
            
            # Clear existing database if force reindex
            if force_reindex and os.path.exists(self.db_manager.db_path):
                import shutil
                shutil.rmtree(self.db_manager.db_path)
                logger.info("Cleared existing vector database for re-indexing")
            
            # Progress callback for logging
            def progress_callback(current: int, total: int):
                logger.info(f"Indexing progress: {current}/{total} files processed")
            
            # Index the directory
            result = await self.db_manager.index_directory(
                directory_path, 
                progress_callback=progress_callback
            )
            
            return ToolResult(output=result, error=None)
            
        except Exception as e:
            error_msg = f"Error indexing directory: {str(e)}"
            logger.error(error_msg)
            return ToolResult(output=None, error=error_msg)

@TOOL.register_module(name="vector_search_tool", force=True)
class VectorSearchTool(AsyncTool):
    """Tool for searching indexed documents"""
    
    name = "vector_search_tool"
    description = "Search through indexed documents using semantic similarity search."
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query to find relevant documents"
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return (default: 5)",
                "default": 5,
                "nullable": True
            }
        },
        "required": ["query"]
    }
    output_type = "any"
    
    def __init__(self,
                 db_path: str = "vector_db",
                 embeddings_model: str = "text-embedding-3-small",
                 **kwargs):
        super().__init__()
        # Ignore any extra kwargs like 'name' from configuration
        
        self.db_manager = VectorDatabaseManager(
            db_path=db_path,
            embeddings_model=embeddings_model
        )
    
    async def forward(self, query: str, max_results: int = 5) -> ToolResult:
        """Search for documents matching the query with comprehensive metadata"""
        try:
            results = self.db_manager.search_documents(query, k=max_results)
            
            if not results:
                return ToolResult(
                    output={
                        'query': query,
                        'results': [],
                        'results_count': 0,
                        'message': 'No relevant documents found in the indexed collection'
                    },
                    error=None
                )
            
            # Format results with comprehensive metadata
            formatted_output = {
                'query': query,
                'results_count': len(results),
                'search_summary': {
                    'total_matches': len(results),
                    'top_similarity': round(results[0]['similarity_score'], 4) if results else 0,
                    'files_found': len(set(r['file_info']['name'] for r in results)),
                    'file_types': list(set(r['file_info']['type'] for r in results))
                },
                'results': []
            }
            
            for result in results:
                # Create beautifully formatted result
                formatted_result = {
                    'rank': result['rank'],
                    'similarity_score': round(result['similarity_score'], 4),
                    'relevance_level': self._get_relevance_level(result['similarity_score']),
                    
                    # Content information
                    'content': {
                        'preview': result['content_preview'],
                        'full_content': result['full_content'],
                        'length': result['content_info']['chunk_length'],
                        'chunk_info': f"Chunk {result['content_info']['chunk_index'] + 1} of {result['content_info']['total_file_chunks']}"
                    },
                    
                    # File information with beautiful formatting
                    'file': {
                        'name': result['file_info']['name'],
                        'path': result['file_info']['path'],
                        'directory': result['file_info']['directory'],
                        'type': result['file_info']['type'],
                        'mime_type': result['file_info']['mime_type'],
                        'size': result['file_info']['size'],
                        'size_bytes': result['file_info']['size_bytes']
                    },
                    
                    # Timestamp information
                    'timestamps': {
                        'created': result['timestamps']['created'],
                        'modified': result['timestamps']['modified'],
                        'indexed': result['timestamps']['indexed'],
                        'last_accessed': result['timestamps']['accessed']
                    },
                    
                    # System metadata
                    'system': {
                        'permissions': result['system_info']['permissions'],
                        'is_hidden': result['system_info']['is_hidden'],
                        'is_symlink': result['system_info']['is_symlink'],
                        'file_hash': result['system_info']['file_hash'][:16] + '...'  # Shortened for display
                    },
                    
                    # Legacy fields for backward compatibility
                    'source_file': result['source_file'],
                    'file_type': result['file_type'],
                    'file_size': result['file_size'],
                    'metadata': result['raw_metadata']
                }
                
                formatted_output['results'].append(formatted_result)
            
            return ToolResult(output=formatted_output, error=None)
            
        except Exception as e:
            error_msg = f"Error searching documents: {str(e)}"
            logger.error(error_msg)
            return ToolResult(
                output={
                    'query': query,
                    'results': [],
                    'results_count': 0,
                    'error_details': error_msg
                }, 
                error=error_msg
            )
    
    def _get_relevance_level(self, similarity_score: float) -> str:
        """Convert similarity score to human-readable relevance level"""
        if similarity_score <= 0.3:
            return "Very High"
        elif similarity_score <= 0.5:
            return "High"
        elif similarity_score <= 0.7:
            return "Medium"
        elif similarity_score <= 0.9:
            return "Low"
        else:
            return "Very Low" 