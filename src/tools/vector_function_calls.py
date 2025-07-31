import json
import os
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
from datetime import datetime

from src.tools import AsyncTool, ToolResult
from src.tools.vector_database import VectorDatabaseManager
from src.registry import TOOL
from src.logger import logger

@TOOL.register_module(name="vector_function_calls_tool", force=True)
class VectorFunctionCallsTool(AsyncTool):
    """
    OpenAI-compatible function calls interface for vector database operations.
    
    This tool exposes vector database functionality through structured function calls
    that can be used programmatically by AI agents and external systems.
    """
    
    name = "vector_function_calls_tool"
    description = "Execute structured function calls to interact with the vector database using OpenAI-compatible function definitions."
    skip_forward_signature_validation = True
    parameters = {
        "type": "object",
        "properties": {
            "function_name": {
                "type": "string",
                "description": "Name of the function to execute",
                "enum": [
                    "search_documents",
                    "get_file_info",
                    "list_indexed_files", 
                    "get_file_content",
                    "search_by_file_type",
                    "search_by_date_range",
                    "get_database_stats",
                    "find_similar_documents"
                ]
            },
            "parameters": {
                "type": "object",
                "description": "Parameters for the function call (JSON object)"
            }
        },
        "required": ["function_name", "parameters"]
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
        
        # OpenAI-compatible function definitions
        self.function_definitions = {
            "search_documents": {
                "name": "search_documents",
                "description": "Search for documents using semantic similarity matching",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query to find relevant documents"
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results to return",
                            "default": 5,
                            "minimum": 1,
                            "maximum": 50,
                            "nullable": True
                        },
                        "min_similarity": {
                            "type": "number",
                            "description": "Minimum similarity score (0.0-1.0)",
                            "default": 0.0,
                            "minimum": 0.0,
                            "maximum": 1.0,
                            "nullable": True
                        }
                    },
                    "required": ["query"]
                }
            },
            
            "get_file_info": {
                "name": "get_file_info",
                "description": "Get detailed metadata information about a specific file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the file (absolute or relative)"
                        }
                    },
                    "required": ["file_path"]
                }
            },
            
            "list_indexed_files": {
                "name": "list_indexed_files",
                "description": "List all files that have been indexed in the vector database",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_type": {
                            "type": "string",
                            "description": "Filter by file type (e.g., '.pdf', '.docx')",
                            "nullable": True
                        },
                        "directory": {
                            "type": "string", 
                            "description": "Filter by directory path",
                            "nullable": True
                        },
                        "sort_by": {
                            "type": "string",
                            "description": "Sort criteria",
                            "enum": ["name", "size", "modified", "created", "indexed"],
                            "default": "modified",
                            "nullable": True
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of files to return",
                            "default": 100,
                            "minimum": 1,
                            "maximum": 1000,
                            "nullable": True
                        }
                    }
                }
            },
            
            "get_file_content": {
                "name": "get_file_content",
                "description": "Get the content of a specific file chunk or entire file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the file"
                        },
                        "chunk_index": {
                            "type": "integer",
                            "description": "Specific chunk index (optional, returns all chunks if not specified)",
                            "nullable": True
                        },
                        "max_length": {
                            "type": "integer",
                            "description": "Maximum content length to return",
                            "default": 5000,
                            "nullable": True
                        }
                    },
                    "required": ["file_path"]
                }
            },
            
            "search_by_file_type": {
                "name": "search_by_file_type",
                "description": "Search for documents of specific file types",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_types": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of file extensions (e.g., ['.pdf', '.docx'])"
                        },
                        "query": {
                            "type": "string",
                            "description": "Optional search query within these file types",
                            "nullable": True
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum results per file type",
                            "default": 10,
                            "nullable": True
                        }
                    },
                    "required": ["file_types"]
                }
            },
            
            "search_by_date_range": {
                "name": "search_by_date_range",
                "description": "Search for documents within a specific date range",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "start_date": {
                            "type": "string",
                            "description": "Start date in ISO format (YYYY-MM-DD)"
                        },
                        "end_date": {
                            "type": "string",
                            "description": "End date in ISO format (YYYY-MM-DD)"
                        },
                        "date_field": {
                            "type": "string",
                            "description": "Date field to filter by",
                            "enum": ["created", "modified", "indexed"],
                            "default": "modified",
                            "nullable": True
                        },
                        "query": {
                            "type": "string",
                            "description": "Optional search query within date range",
                            "nullable": True
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 20,
                            "nullable": True
                        }
                    },
                    "required": ["start_date", "end_date"]
                }
            },
            
            "get_database_stats": {
                "name": "get_database_stats",
                "description": "Get comprehensive statistics about the vector database",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "include_file_list": {
                            "type": "boolean",
                            "description": "Include detailed file list in response",
                            "default": False,
                            "nullable": True
                        }
                    }
                }
            },
            
            "find_similar_documents": {
                "name": "find_similar_documents",
                "description": "Find documents similar to a specific document",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reference_file": {
                            "type": "string",
                            "description": "Path to the reference file"
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of similar documents to return",
                            "default": 10,
                            "nullable": True
                        },
                        "exclude_same_file": {
                            "type": "boolean",
                            "description": "Exclude chunks from the same file",
                            "default": True,
                            "nullable": True
                        }
                    },
                    "required": ["reference_file"]
                }
            }
        }
    
    def get_function_definitions(self) -> List[Dict[str, Any]]:
        """Get OpenAI-compatible function definitions"""
        return list(self.function_definitions.values())
    
    def _validate_parameters(self, function_name: str, parameters: Dict[str, Any]) -> Optional[str]:
        """Validate parameters against function definition schema.
        
        Returns:
            None if valid, error message string if invalid
        """
        if function_name not in self.function_definitions:
            return f"Unknown function: {function_name}"
        
        func_def = self.function_definitions[function_name]
        required_params = func_def.get("parameters", {}).get("required", [])
        
        # Check required parameters
        for param in required_params:
            if param not in parameters:
                return f"Missing required parameter '{param}' for function '{function_name}'"
        
        # Validate parameter types (basic validation)
        param_props = func_def.get("parameters", {}).get("properties", {})
        for param_name, param_value in parameters.items():
            if param_name in param_props:
                expected_type = param_props[param_name].get("type")
                if expected_type == "string" and not isinstance(param_value, str):
                    return f"Parameter '{param_name}' must be a string, got {type(param_value).__name__}"
                elif expected_type == "integer" and not isinstance(param_value, int):
                    return f"Parameter '{param_name}' must be an integer, got {type(param_value).__name__}"
                elif expected_type == "number" and not isinstance(param_value, (int, float)):
                    return f"Parameter '{param_name}' must be a number, got {type(param_value).__name__}"
                elif expected_type == "boolean" and not isinstance(param_value, bool):
                    return f"Parameter '{param_name}' must be a boolean, got {type(param_value).__name__}"
                elif expected_type == "array" and not isinstance(param_value, list):
                    return f"Parameter '{param_name}' must be an array, got {type(param_value).__name__}"
        
        return None
    
    async def _search_documents(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle search_documents function call"""
        # Validate required parameters
        if "query" not in parameters:
            return {
                "function": "search_documents",
                "success": False,
                "error": "Missing required parameter 'query'",
                "required_parameters": ["query"],
                "optional_parameters": ["max_results", "min_similarity"],
                "parameters_received": list(parameters.keys())
            }
        
        query = parameters["query"]
        if not query or not isinstance(query, str):
            return {
                "function": "search_documents",
                "success": False,
                "error": "Parameter 'query' must be a non-empty string",
                "parameters_received": parameters
            }
        
        max_results = parameters.get("max_results", 5)
        min_similarity = parameters.get("min_similarity", 0.0)
        
        # Validate optional parameters
        if not isinstance(max_results, int) or max_results < 1 or max_results > 50:
            max_results = 5
            
        if not isinstance(min_similarity, (int, float)) or min_similarity < 0.0 or min_similarity > 1.0:
            min_similarity = 0.0
        
        try:
            results = self.db_manager.search_documents(query, k=max_results)
            
            # Filter by minimum similarity
            filtered_results = [
                r for r in results 
                if r.get("similarity_score", 1.0) >= min_similarity
            ]
            
            return {
                "function": "search_documents",
                "success": True,
                "query": query,
                "total_results": len(filtered_results),
                "parameters_used": {
                    "query": query,
                    "max_results": max_results,
                    "min_similarity": min_similarity
                },
                "results": filtered_results
            }
            
        except Exception as e:
            logger.error(f"Database search error: {str(e)}")
            return {
                "function": "search_documents", 
                "success": False,
                "error": f"Database search failed: {str(e)}",
                "parameters_used": parameters
            }
    
    async def _get_file_info(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get_file_info function call"""
        if "file_path" not in parameters:
            return {
                "function": "get_file_info",
                "success": False,
                "error": "Missing required parameter 'file_path'",
                "required_parameters": ["file_path"]
            }
        
        file_path = parameters["file_path"]
        if not isinstance(file_path, str) or not file_path.strip():
            return {
                "function": "get_file_info",
                "success": False,
                "error": "Parameter 'file_path' must be a non-empty string"
            }
        
        try:
            # Search for the specific file in the database
            results = self.db_manager.search_documents(f"file:{file_path}", k=50)
            
            # Find exact file match
            file_results = [
                r for r in results 
                if r.get("source_file") == file_path or 
                   r.get("file_info", {}).get("path") == file_path or
                   r.get("file_info", {}).get("name") == Path(file_path).name
            ]
            
            if not file_results:
                return {
                    "function": "get_file_info",
                    "success": False,
                    "error": f"File not found in database: {file_path}",
                    "parameters_used": parameters
                }
            
            # Get the most complete metadata from the first result
            file_info = file_results[0]
            
            # Aggregate information from all chunks of this file
            total_chunks = len(file_results)
            total_content_length = sum(
                r.get("content_info", {}).get("chunk_length", 0) 
                for r in file_results
            )
            
            return {
                "function": "get_file_info",
                "success": True,
                "file_path": file_path,
                "file_info": file_info.get("file_info", {}),
                "timestamps": file_info.get("timestamps", {}),
                "system_info": file_info.get("system_info", {}),
                "content_summary": {
                    "total_chunks": total_chunks,
                    "total_content_length": total_content_length,
                    "chunks_available": len(file_results)
                },
                "parameters_used": parameters
            }
            
        except Exception as e:
            logger.error(f"Get file info error: {str(e)}")
            return {
                "function": "get_file_info",
                "success": False,
                "error": f"Failed to get file info: {str(e)}",
                "parameters_used": parameters
            }
    
    async def _list_indexed_files(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle list_indexed_files function call"""
        file_type = parameters.get("file_type")
        directory = parameters.get("directory")
        sort_by = parameters.get("sort_by", "modified")
        limit = parameters.get("limit", 100)
        
        # Validate parameters
        if sort_by not in ["name", "size", "modified", "created", "indexed"]:
            sort_by = "modified"
        
        if not isinstance(limit, int) or limit < 1 or limit > 1000:
            limit = 100
        
        try:
            # Get all documents to extract unique files
            all_results = self.db_manager.search_documents("*", k=10000)  # Large number to get all
            
            # Group by file to get unique files
            files_dict = {}
            for result in all_results:
                file_path = result.get("source_file") or result.get("file_info", {}).get("path")
                if not file_path:
                    continue
                    
                if file_path not in files_dict:
                    files_dict[file_path] = result
            
            files_list = list(files_dict.values())
            
            # Apply filters
            if file_type:
                files_list = [
                    f for f in files_list 
                    if f.get("file_info", {}).get("type", "").lower() == file_type.lower()
                ]
            
            if directory:
                files_list = [
                    f for f in files_list
                    if directory in f.get("file_info", {}).get("directory", "")
                ]
            
            # Sort files
            sort_key_map = {
                "name": lambda x: x.get("file_info", {}).get("name", ""),
                "size": lambda x: x.get("file_info", {}).get("size_bytes", 0),
                "modified": lambda x: x.get("timestamps", {}).get("modified", ""),
                "created": lambda x: x.get("timestamps", {}).get("created", ""),
                "indexed": lambda x: x.get("timestamps", {}).get("indexed", "")
            }
            
            if sort_by in sort_key_map:
                files_list.sort(key=sort_key_map[sort_by], reverse=True)
            
            # Apply limit
            files_list = files_list[:limit]
            
            # Format response
            formatted_files = []
            for file_data in files_list:
                formatted_files.append({
                    "file_info": file_data.get("file_info", {}),
                    "timestamps": file_data.get("timestamps", {}),
                    "system_info": file_data.get("system_info", {}),
                    "content_summary": file_data.get("content_info", {})
                })
            
            return {
                "function": "list_indexed_files",
                "success": True,
                "total_files": len(formatted_files),
                "filters_applied": {
                    "file_type": file_type,
                    "directory": directory,
                    "sort_by": sort_by
                },
                "files": formatted_files,
                "parameters_used": parameters
            }
            
        except Exception as e:
            logger.error(f"List indexed files error: {str(e)}")
            return {
                "function": "list_indexed_files",
                "success": False,
                "error": f"Failed to list indexed files: {str(e)}",
                "parameters_used": parameters
            }
    
    async def _get_file_content(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get_file_content function call"""
        if "file_path" not in parameters:
            return {
                "function": "get_file_content",
                "success": False,
                "error": "Missing required parameter 'file_path'",
                "required_parameters": ["file_path"]
            }
        
        file_path = parameters["file_path"]
        chunk_index = parameters.get("chunk_index")
        max_length = parameters.get("max_length", 5000)
        
        if not isinstance(file_path, str) or not file_path.strip():
            return {
                "function": "get_file_content",
                "success": False,
                "error": "Parameter 'file_path' must be a non-empty string"
            }
        
        try:
            # Search for the specific file
            results = self.db_manager.search_documents(f"file:{file_path}", k=100)
            
            # Find matching file chunks
            file_chunks = [
                r for r in results
                if r.get("source_file") == file_path or
                   r.get("file_info", {}).get("path") == file_path
            ]
            
            if not file_chunks:
                return {
                    "function": "get_file_content",
                    "success": False,
                    "error": f"File not found: {file_path}",
                    "parameters_used": parameters
                }
            
            # Sort chunks by chunk index
            file_chunks.sort(key=lambda x: x.get("content_info", {}).get("chunk_index", 0))
            
            if chunk_index is not None:
                # Return specific chunk
                target_chunk = None
                for chunk in file_chunks:
                    if chunk.get("content_info", {}).get("chunk_index") == chunk_index:
                        target_chunk = chunk
                        break
                
                if not target_chunk:
                    return {
                        "function": "get_file_content",
                        "success": False,
                        "error": f"Chunk {chunk_index} not found in file {file_path}",
                        "parameters_used": parameters
                    }
                
                content = target_chunk.get("content", {}).get("full_content", "")
                if len(content) > max_length:
                    content = content[:max_length] + "..."
                
                return {
                    "function": "get_file_content",
                    "success": True,
                    "file_path": file_path,
                    "chunk_index": chunk_index,
                    "content": content,
                    "content_info": target_chunk.get("content_info", {}),
                    "parameters_used": parameters
                }
            else:
                # Return all chunks (up to max_length total)
                all_content = []
                total_length = 0
                
                for chunk in file_chunks:
                    chunk_content = chunk.get("content", {}).get("full_content", "")
                    if total_length + len(chunk_content) > max_length:
                        remaining = max_length - total_length
                        if remaining > 0:
                            all_content.append(chunk_content[:remaining] + "...")
                        break
                    
                    all_content.append(chunk_content)
                    total_length += len(chunk_content)
                
                return {
                    "function": "get_file_content",
                    "success": True,
                    "file_path": file_path,
                    "total_chunks": len(file_chunks),
                    "content": "\n\n".join(all_content),
                    "content_length": total_length,
                    "truncated": total_length >= max_length,
                    "parameters_used": parameters
                }
                
        except Exception as e:
            logger.error(f"Get file content error: {str(e)}")
            return {
                "function": "get_file_content",
                "success": False,
                "error": f"Failed to get file content: {str(e)}",
                "parameters_used": parameters
            }
    
    async def _search_by_file_type(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle search_by_file_type function call"""
        if "file_types" not in parameters:
            return {
                "function": "search_by_file_type",
                "success": False,
                "error": "Missing required parameter 'file_types'",
                "required_parameters": ["file_types"]
            }
        
        file_types = parameters["file_types"]
        query = parameters.get("query", "")
        max_results = parameters.get("max_results", 10)
        
        if not isinstance(file_types, list) or not file_types:
            return {
                "function": "search_by_file_type",
                "success": False,
                "error": "Parameter 'file_types' must be a non-empty list of strings"
            }
        
        try:
            all_results = []
            
            for file_type in file_types:
                # Search for documents of this file type
                if query:
                    search_query = f"{query} filetype:{file_type}"
                else:
                    search_query = f"filetype:{file_type}"
                
                results = self.db_manager.search_documents(search_query, k=max_results)
                
                # Filter by actual file type
                filtered_results = [
                    r for r in results
                    if r.get("file_info", {}).get("type", "").lower() == file_type.lower()
                ]
                
                all_results.extend(filtered_results[:max_results])
            
            return {
                "function": "search_by_file_type",
                "success": True,
                "file_types": file_types,
                "query": query,
                "total_results": len(all_results),
                "results": all_results,
                "parameters_used": parameters
            }
            
        except Exception as e:
            logger.error(f"Search by file type error: {str(e)}")
            return {
                "function": "search_by_file_type",
                "success": False,
                "error": f"Failed to search by file type: {str(e)}",
                "parameters_used": parameters
            }
    
    async def _search_by_date_range(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle search_by_date_range function call"""
        required_params = ["start_date", "end_date"]
        missing_params = [p for p in required_params if p not in parameters]
        
        if missing_params:
            return {
                "function": "search_by_date_range",
                "success": False,
                "error": f"Missing required parameters: {missing_params}",
                "required_parameters": required_params
            }
        
        start_date = parameters["start_date"]
        end_date = parameters["end_date"]
        date_field = parameters.get("date_field", "modified")
        query = parameters.get("query", "")
        max_results = parameters.get("max_results", 20)
        
        try:
            # Get all documents first
            if query:
                results = self.db_manager.search_documents(query, k=max_results * 2)
            else:
                results = self.db_manager.search_documents("*", k=1000)
            
            # Filter by date range
            filtered_results = []
            
            for result in results:
                date_str = result.get("timestamps", {}).get(date_field)
                if not date_str:
                    continue
                
                try:
                    # Parse date (assuming ISO format)
                    file_date = datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
                    start = datetime.fromisoformat(start_date).date()
                    end = datetime.fromisoformat(end_date).date()
                    
                    if start <= file_date <= end:
                        filtered_results.append(result)
                        
                except ValueError:
                    continue
            
            # Limit results
            filtered_results = filtered_results[:max_results]
            
            return {
                "function": "search_by_date_range",
                "success": True,
                "date_range": {"start": start_date, "end": end_date},
                "date_field": date_field,
                "query": query,
                "total_results": len(filtered_results),
                "results": filtered_results,
                "parameters_used": parameters
            }
            
        except Exception as e:
            logger.error(f"Search by date range error: {str(e)}")
            return {
                "function": "search_by_date_range",
                "success": False,
                "error": f"Failed to search by date range: {str(e)}",
                "parameters_used": parameters
            }
    
    async def _get_database_stats(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get_database_stats function call"""
        include_file_list = parameters.get("include_file_list", False)
        
        try:
            # Get all documents to compute statistics
            all_results = self.db_manager.search_documents("*", k=10000)
            
            # Compute statistics
            unique_files = {}
            file_types = {}
            total_content_length = 0
            total_chunks = len(all_results)
            
            for result in all_results:
                # Track unique files
                file_path = result.get("source_file") or result.get("file_info", {}).get("path")
                if file_path and file_path not in unique_files:
                    unique_files[file_path] = result
                
                # Track file types
                file_type = result.get("file_info", {}).get("type", "unknown")
                file_types[file_type] = file_types.get(file_type, 0) + 1
                
                # Track content length
                content_length = result.get("content_info", {}).get("chunk_length", 0)
                total_content_length += content_length
            
            # Calculate size statistics
            total_files = len(unique_files)
            file_sizes = [
                f.get("file_info", {}).get("size_bytes", 0) 
                for f in unique_files.values()
            ]
            total_size_bytes = sum(file_sizes)
            avg_file_size = total_size_bytes / total_files if total_files > 0 else 0
            
            # Database info
            db_exists = os.path.exists(self.db_manager.db_path)
            db_size = 0
            if db_exists:
                try:
                    db_path = Path(self.db_manager.db_path)
                    db_size = sum(f.stat().st_size for f in db_path.rglob('*') if f.is_file())
                except:
                    pass
            
            stats = {
                "function": "get_database_stats",
                "success": True,
                "database_info": {
                    "path": self.db_manager.db_path,
                    "exists": db_exists,
                    "size_bytes": db_size,
                    "size_mb": round(db_size / (1024 * 1024), 2)
                },
                "content_stats": {
                    "total_files": total_files,
                    "total_chunks": total_chunks,
                    "total_content_length": total_content_length,
                    "avg_chunks_per_file": round(total_chunks / total_files, 2) if total_files > 0 else 0
                },
                "file_stats": {
                    "total_size_bytes": total_size_bytes,
                    "total_size_mb": round(total_size_bytes / (1024 * 1024), 2),
                    "avg_file_size_bytes": round(avg_file_size),
                    "avg_file_size_mb": round(avg_file_size / (1024 * 1024), 2)
                },
                "file_types": file_types,
                "parameters_used": parameters
            }
            
            if include_file_list:
                stats["files"] = [
                    {
                        "path": path,
                        "info": data.get("file_info", {}),
                        "timestamps": data.get("timestamps", {})
                    }
                    for path, data in unique_files.items()
                ]
            
            return stats
            
        except Exception as e:
            logger.error(f"Get database stats error: {str(e)}")
            return {
                "function": "get_database_stats",
                "success": False,
                "error": f"Failed to get database stats: {str(e)}",
                "parameters_used": parameters
            }
    
    async def _find_similar_documents(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle find_similar_documents function call"""
        if "reference_file" not in parameters:
            return {
                "function": "find_similar_documents",
                "success": False,
                "error": "Missing required parameter 'reference_file'",
                "required_parameters": ["reference_file"]
            }
        
        reference_file = parameters["reference_file"]
        max_results = parameters.get("max_results", 10)
        exclude_same_file = parameters.get("exclude_same_file", True)
        
        if not isinstance(reference_file, str) or not reference_file.strip():
            return {
                "function": "find_similar_documents",
                "success": False,
                "error": "Parameter 'reference_file' must be a non-empty string"
            }
        
        try:
            # First, get content from the reference file
            ref_results = self.db_manager.search_documents(f"file:{reference_file}", k=10)
            
            if not ref_results:
                return {
                    "function": "find_similar_documents",
                    "success": False,
                    "error": f"Reference file not found: {reference_file}",
                    "parameters_used": parameters
                }
            
            # Use the content of the first chunk as search query
            ref_content = ref_results[0].get("content", {}).get("full_content", "")
            if not ref_content:
                ref_content = ref_results[0].get("content_preview", "")
            
            # Search for similar documents using the content
            similar_results = self.db_manager.search_documents(ref_content[:1000], k=max_results * 2)
            
            # Filter out the reference file if requested
            if exclude_same_file:
                similar_results = [
                    r for r in similar_results
                    if r.get("source_file") != reference_file and
                       r.get("file_info", {}).get("path") != reference_file
                ]
            
            # Limit results
            similar_results = similar_results[:max_results]
            
            return {
                "function": "find_similar_documents",
                "success": True,
                "reference_file": reference_file,
                "total_similar": len(similar_results),
                "similar_documents": similar_results,
                "parameters_used": parameters
            }
            
        except Exception as e:
            logger.error(f"Find similar documents error: {str(e)}")
            return {
                "function": "find_similar_documents",
                "success": False,
                "error": f"Failed to find similar documents: {str(e)}",
                "parameters_used": parameters
            }
    
    async def forward(self, *args, **kwargs) -> ToolResult:
        """Execute the specified function call"""
        
        # Add detailed logging for debugging
        logger.debug(f"VectorFunctionCallsTool.forward called with args={args}, kwargs={kwargs}")
        
        # Handle different input patterns
        function_name = None
        parameters = {}
        
        # Pattern 1: function_name and parameters as separate arguments
        if len(args) >= 2:
            function_name = args[0]
            parameters = args[1] if isinstance(args[1], dict) else {}
        # Pattern 2: single string argument (function name)
        elif len(args) == 1 and isinstance(args[0], str):
            function_name = args[0]
            parameters = {}
        # Pattern 3: single dict argument
        elif len(args) == 1 and isinstance(args[0], dict):
            # Check if it has function_name and parameters keys
            if 'function_name' in args[0] and 'parameters' in args[0]:
                function_name = args[0]['function_name']
                parameters = args[0]['parameters']
            else:
                # Assume it's parameters for a default function
                function_name = "search_documents"
                parameters = args[0]
        
        # Pattern 4: keyword arguments
        if function_name is None:
            function_name = kwargs.get('function_name')
        if not parameters:
            parameters = kwargs.get('parameters', {})
        
        # If still no function_name, try to get it from the first kwarg
        if function_name is None and kwargs:
            # Get the first key that's not 'parameters'
            for key, value in kwargs.items():
                if key != 'parameters':
                    function_name = key
                    parameters = value if isinstance(value, dict) else {}
                    break
        
        # Handle case where parameters might be a string (fallback)
        if isinstance(parameters, str):
            logger.warning(f"Parameters is a string instead of dict: {parameters}")
            # If parameters is a string, treat it as a query for search_documents
            if function_name == "search_documents":
                parameters = {"query": parameters}
                logger.info(f"Converted string parameter to dict for search_documents: {parameters}")
            else:
                return ToolResult(
                    output={
                        "success": False,
                        "error": f"Parameters must be a dictionary, got string: {parameters}",
                        "expected_format": "parameters should be a JSON object with function-specific parameters"
                    },
                    error="Invalid parameters type"
                )
        
        # Ensure parameters is a dictionary
        if not isinstance(parameters, dict):
            logger.warning(f"Parameters is not a dict: {type(parameters)} = {parameters}")
            parameters = {}
        
        # Final validation
        if function_name is None:
            return ToolResult(
                output={
                    "success": False,
                    "error": "No function_name provided",
                    "usage_examples": [
                        "forward('search_documents', {'query': 'test'})",
                        "forward(function_name='search_documents', parameters={'query': 'test'})"
                    ],
                    "available_functions": list(self.function_definitions.keys())
                },
                error="No function_name provided"
            )
        
        # Validate function name
        if function_name not in self.function_definitions:
            return ToolResult(
                output={
                    "success": False,
                    "error": f"Unknown function: {function_name}",
                    "available_functions": list(self.function_definitions.keys())
                },
                error=f"Unknown function: {function_name}"
            )
        
        # Validate parameters using schema
        validation_error = self._validate_parameters(function_name, parameters)
        if validation_error:
            function_def = self.function_definitions[function_name]
            return ToolResult(
                output={
                    "success": False,
                    "error": validation_error,
                    "function": function_name,
                    "required_parameters": function_def.get("parameters", {}).get("required", []),
                    "all_parameters": list(function_def.get("parameters", {}).get("properties", {}).keys()),
                    "parameters_received": list(parameters.keys()) if parameters else []
                },
                error=validation_error
            )
        
        try:
            # Route to appropriate handler
            if function_name == "search_documents":
                result = await self._search_documents(parameters)
            elif function_name == "get_file_info":
                result = await self._get_file_info(parameters)
            elif function_name == "list_indexed_files":
                result = await self._list_indexed_files(parameters)
            elif function_name == "get_file_content":
                result = await self._get_file_content(parameters)
            elif function_name == "search_by_file_type":
                result = await self._search_by_file_type(parameters)
            elif function_name == "search_by_date_range":
                result = await self._search_by_date_range(parameters)
            elif function_name == "get_database_stats":
                result = await self._get_database_stats(parameters)
            elif function_name == "find_similar_documents":
                result = await self._find_similar_documents(parameters)
            else:
                result = {
                    "success": False,
                    "error": f"Handler not implemented for function: {function_name}"
                }
            
            return ToolResult(output=result, error=None if result.get("success") else result.get("error"))
            
        except Exception as e:
            error_msg = f"Error executing function {function_name}: {str(e)}"
            logger.error(error_msg)
            logger.error(f"Function: {function_name}, Parameters: {parameters}, Error: {e}")
            
            return ToolResult(
                output={
                    "function": function_name,
                    "success": False,
                    "error": error_msg,
                    "parameters_used": parameters
                },
                error=error_msg
            )