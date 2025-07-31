"""
Vector Database API Service

This module provides a RESTful API service that exposes vector database operations
through OpenAI-compatible function calls. It can be used by external applications,
AI agents, and integration systems.
"""

import json
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import time

from src.tools.vector_function_calls import VectorFunctionCallsTool
from src.logger import logger


@dataclass
class FunctionCallRequest:
    """Structured request for function calls"""
    function_name: str
    parameters: Dict[str, Any]
    request_id: Optional[str] = None
    timestamp: Optional[float] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.request_id is None:
            self.request_id = f"req_{int(self.timestamp)}_{hash(self.function_name)}"


@dataclass 
class FunctionCallResponse:
    """Structured response for function calls"""
    success: bool
    result: Dict[str, Any]
    request_id: str
    function_name: str
    execution_time: float
    timestamp: float
    error: Optional[str] = None


class VectorAPIService:
    """
    API Service for vector database operations using OpenAI-compatible function calls.
    
    This service provides a high-level interface for programmatic access to the vector database
    with structured function calls, request/response handling, and comprehensive error management.
    """
    
    def __init__(self, 
                 db_path: str = "vector_db",
                 embeddings_model: str = "text-embedding-3-small"):
        
        self.function_tool = VectorFunctionCallsTool(
            db_path=db_path,
            embeddings_model=embeddings_model
        )
        
        # Service metadata
        self.service_info = {
            "name": "Vector Database API Service",
            "version": "1.0.0",
            "description": "OpenAI-compatible function calls for vector database operations",
            "db_path": db_path,
            "embeddings_model": embeddings_model
        }
        
        # Request tracking
        self.request_history = []
        self.max_history = 1000
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get service information and capabilities"""
        return {
            **self.service_info,
            "available_functions": list(self.function_tool.function_definitions.keys()),
            "total_requests_processed": len(self.request_history),
            "uptime_seconds": time.time() - getattr(self, '_start_time', time.time())
        }
    
    def get_function_definitions(self) -> List[Dict[str, Any]]:
        """Get OpenAI-compatible function definitions"""
        return self.function_tool.get_function_definitions()
    
    def get_function_schema(self, function_name: str) -> Optional[Dict[str, Any]]:
        """Get schema for a specific function"""
        return self.function_tool.function_definitions.get(function_name)
    
    async def execute_function_call(self, request: FunctionCallRequest) -> FunctionCallResponse:
        """Execute a function call with full request/response handling"""
        start_time = time.time()
        
        try:
            logger.info(f"Executing function call: {request.function_name} (ID: {request.request_id})")
            
            # Validate function exists
            if request.function_name not in self.function_tool.function_definitions:
                raise ValueError(f"Unknown function: {request.function_name}")
            
            # Execute the function
            tool_result = await self.function_tool.forward(
                request.function_name, 
                request.parameters
            )
            
            execution_time = time.time() - start_time
            
            # Create response
            response = FunctionCallResponse(
                success=tool_result.error is None,
                result=tool_result.output,
                request_id=request.request_id,
                function_name=request.function_name,
                execution_time=execution_time,
                timestamp=time.time(),
                error=tool_result.error
            )
            
            # Track request
            self._add_to_history(request, response)
            
            logger.info(f"Function call completed: {request.function_name} in {execution_time:.3f}s")
            
            return response
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Function call failed: {str(e)}"
            
            logger.error(f"Error in function call {request.function_name}: {e}")
            
            response = FunctionCallResponse(
                success=False,
                result={"error_details": error_msg},
                request_id=request.request_id,
                function_name=request.function_name,
                execution_time=execution_time,
                timestamp=time.time(),
                error=error_msg
            )
            
            self._add_to_history(request, response)
            
            return response
    
    def _add_to_history(self, request: FunctionCallRequest, response: FunctionCallResponse):
        """Add request/response to history with size management"""
        self.request_history.append({
            "request": {
                "id": request.request_id,
                "function": request.function_name,
                "parameters": request.parameters,
                "timestamp": request.timestamp
            },
            "response": {
                "success": response.success,
                "execution_time": response.execution_time,
                "timestamp": response.timestamp,
                "error": response.error
            }
        })
        
        # Maintain history size limit
        if len(self.request_history) > self.max_history:
            self.request_history = self.request_history[-self.max_history:]
    
    async def batch_execute(self, requests: List[FunctionCallRequest]) -> List[FunctionCallResponse]:
        """Execute multiple function calls in parallel"""
        logger.info(f"Executing batch of {len(requests)} function calls")
        
        tasks = [
            self.execute_function_call(request) 
            for request in requests
        ]
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to error responses
        final_responses = []
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                error_response = FunctionCallResponse(
                    success=False,
                    result={"error_details": str(response)},
                    request_id=requests[i].request_id,
                    function_name=requests[i].function_name,
                    execution_time=0,
                    timestamp=time.time(),
                    error=str(response)
                )
                final_responses.append(error_response)
            else:
                final_responses.append(response)
        
        return final_responses
    
    def get_request_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent request history"""
        return self.request_history[-limit:]
    
    def get_function_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics for each function"""
        function_stats = {}
        
        for entry in self.request_history:
            func_name = entry["request"]["function"]
            
            if func_name not in function_stats:
                function_stats[func_name] = {
                    "total_calls": 0,
                    "successful_calls": 0,
                    "failed_calls": 0,
                    "avg_execution_time": 0,
                    "total_execution_time": 0
                }
            
            stats = function_stats[func_name]
            stats["total_calls"] += 1
            
            if entry["response"]["success"]:
                stats["successful_calls"] += 1
            else:
                stats["failed_calls"] += 1
            
            exec_time = entry["response"]["execution_time"]
            stats["total_execution_time"] += exec_time
            stats["avg_execution_time"] = stats["total_execution_time"] / stats["total_calls"]
        
        return function_stats
    
    # Convenience methods for common operations
    
    async def search_documents(self, query: str, max_results: int = 5, min_similarity: float = 0.0) -> FunctionCallResponse:
        """Convenience method for document search"""
        request = FunctionCallRequest(
            function_name="search_documents",
            parameters={
                "query": query,
                "max_results": max_results,
                "min_similarity": min_similarity
            }
        )
        return await self.execute_function_call(request)
    
    async def get_file_info(self, file_path: str) -> FunctionCallResponse:
        """Convenience method for getting file information"""
        request = FunctionCallRequest(
            function_name="get_file_info",
            parameters={"file_path": file_path}
        )
        return await self.execute_function_call(request)
    
    async def list_files(self, file_type: str = None, directory: str = None, limit: int = 100) -> FunctionCallResponse:
        """Convenience method for listing indexed files"""
        parameters = {"limit": limit}
        if file_type:
            parameters["file_type"] = file_type
        if directory:
            parameters["directory"] = directory
            
        request = FunctionCallRequest(
            function_name="list_indexed_files",
            parameters=parameters
        )
        return await self.execute_function_call(request)
    
    async def get_database_stats(self, include_file_list: bool = False) -> FunctionCallResponse:
        """Convenience method for getting database statistics"""
        request = FunctionCallRequest(
            function_name="get_database_stats",
            parameters={"include_file_list": include_file_list}
        )
        return await self.execute_function_call(request)


# Global service instance
_service_instance = None

def get_vector_api_service(db_path: str = "vector_db", embeddings_model: str = "text-embedding-3-small") -> VectorAPIService:
    """Get or create global service instance"""
    global _service_instance
    
    if _service_instance is None:
        _service_instance = VectorAPIService(db_path=db_path, embeddings_model=embeddings_model)
        _service_instance._start_time = time.time()
        logger.info("Vector API Service initialized")
    
    return _service_instance


# Example usage functions

async def example_search_usage():
    """Example of how to use the API service for search"""
    service = get_vector_api_service()
    
    # Search for documents
    response = await service.search_documents("clinical trials", max_results=10)
    
    if response.success:
        print(f"Found {response.result.get('total_results', 0)} documents")
        for i, doc in enumerate(response.result.get('results', []), 1):
            file_info = doc.get('file_info', {})
            print(f"{i}. {file_info.get('name', 'Unknown')} - {doc.get('relevance_level', 'Unknown')}")
    else:
        print(f"Search failed: {response.error}")

async def example_file_info_usage():
    """Example of how to get file information"""
    service = get_vector_api_service()
    
    # List all PDF files
    files_response = await service.list_files(file_type=".pdf", limit=10)
    
    if files_response.success and files_response.result.get('files'):
        # Get detailed info for the first file
        first_file = files_response.result['files'][0]
        file_path = first_file.get('file_info', {}).get('path', '')
        
        info_response = await service.get_file_info(file_path)
        
        if info_response.success:
            file_info = info_response.result.get('file_info', {})
            print(f"File: {file_info.get('name', 'Unknown')}")
            print(f"Size: {file_info.get('size', 'Unknown')}")
            print(f"Modified: {info_response.result.get('timestamps', {}).get('modified', 'Unknown')}")

async def example_stats_usage():
    """Example of how to get database statistics"""
    service = get_vector_api_service()
    
    # Get comprehensive database stats
    stats_response = await service.get_database_stats(include_file_list=False)
    
    if stats_response.success:
        stats = stats_response.result
        print("Vector Database Statistics:")
        print(f"  Total Files: {stats.get('content_stats', {}).get('total_files', 0)}")
        print(f"  Total Chunks: {stats.get('content_stats', {}).get('total_chunks', 0)}")
        print(f"  Database Size: {stats.get('database_info', {}).get('size_mb', 0)} MB")
        print(f"  File Types: {stats.get('file_types', {})}")

if __name__ == "__main__":
    # Example usage
    async def main():
        print("Vector API Service Examples")
        print("=" * 40)
        
        await example_search_usage()
        print()
        await example_file_info_usage()
        print()
        await example_stats_usage()
        
        # Get service info
        service = get_vector_api_service()
        info = service.get_service_info()
        print(f"\nService Info: {info['name']} v{info['version']}")
        print(f"Available functions: {len(info['available_functions'])}")
    
    asyncio.run(main()) 