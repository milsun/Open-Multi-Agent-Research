from typing import List, Dict, Any, Optional
import asyncio
import json
from pathlib import Path

from src.agent.general_agent import GeneralAgent
from src.tools import VectorSearchTool, ToolResult
from src.models import ChatMessage, MessageRole, Model
from src.base.async_multistep_agent import PromptTemplates
from src.logger import logger
from src.registry import AGENT
from src.utils import assemble_project_path

@AGENT.register_module(name="vector_agent", force=True)
class VectorAgent(GeneralAgent):
    """
    Specialized agent for querying and analyzing documents in the vector database.
    
    This agent excels at:
    - Semantic search across indexed documents
    - Context retrieval and summarization
    - Document analysis and cross-referencing
    - Knowledge extraction from local document collections
    """
    
    def __init__(self,
                 config,
                 tools: list[Any],
                 model: Model,
                 prompt_templates: PromptTemplates | None = None,
                 planning_interval: int | None = None,
                 stream_outputs: bool = False,
                 max_tool_threads: int | None = None,
                 db_path: str = "vector_db",
                 max_search_results: int = 10,
                 similarity_threshold: float = 0.7,
                 **kwargs):
        
        super().__init__(
            config=config,
            tools=tools,
            model=model,
            prompt_templates=prompt_templates,
            planning_interval=planning_interval,
            stream_outputs=stream_outputs,
            max_tool_threads=max_tool_threads,
            **kwargs
        )
        
        # Vector-specific configuration
        self.db_path = db_path
        self.max_search_results = max_search_results
        self.similarity_threshold = similarity_threshold
        
        # Initialize vector search tool
        self.vector_search_tool = VectorSearchTool(db_path=db_path)
        
        # Document context management
        self.current_context = []
        self.processed_queries = []
    
    async def _check_vector_database_status(self) -> Dict[str, Any]:
        """Check if vector database exists and is accessible"""
        try:
            # Test search to verify database accessibility
            test_result = await self.vector_search_tool.forward("test query", max_results=1)
            
            if test_result.error:
                return {
                    "available": False,
                    "error": test_result.error,
                    "message": "Vector database is not accessible"
                }
            
            # Check if any documents are indexed
            if test_result.output['results_count'] == 0:
                return {
                    "available": True,
                    "indexed_documents": 0,
                    "message": "Vector database is empty - no documents indexed yet"
                }
            
            return {
                "available": True,
                "indexed_documents": "available",
                "message": "Vector database is ready and contains indexed documents"
            }
            
        except Exception as e:
            return {
                "available": False,
                "error": str(e),
                "message": "Failed to access vector database"
            }
    
    async def _perform_semantic_search(self, query: str, max_results: int = None) -> Dict[str, Any]:
        """Perform semantic search with enhanced result processing"""
        if max_results is None:
            max_results = self.max_search_results
        
        try:
            # Perform vector search
            result = await self.vector_search_tool.forward(query, max_results=max_results)
            
            if result.error:
                return {
                    "success": False,
                    "error": result.error,
                    "results": []
                }
            
            search_output = result.output
            
            # Filter results by similarity threshold if needed
            filtered_results = []
            if "results" in search_output:
                for doc_result in search_output["results"]:
                    if doc_result.get("similarity_score", 0) >= self.similarity_threshold:
                        filtered_results.append(doc_result)
            
            # Enhance results with additional metadata
            enhanced_results = []
            for doc_result in filtered_results:
                enhanced_result = {
                    "content": doc_result.get("full_content", doc_result.get("content_preview", "")),
                    "source_file": doc_result.get("source_file", "Unknown"),
                    "file_type": doc_result.get("file_type", "Unknown"),
                    "similarity_score": doc_result.get("similarity_score", 0),
                    "rank": doc_result.get("rank", 0),
                    "preview": doc_result.get("content_preview", "")
                }
                enhanced_results.append(enhanced_result)
            
            return {
                "success": True,
                "query": query,
                "total_results": len(enhanced_results),
                "results": enhanced_results,
                "search_metadata": {
                    "original_query": query,
                    "max_results_requested": max_results,
                    "similarity_threshold": self.similarity_threshold,
                    "filtered_count": len(filtered_results)
                }
            }
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": []
            }
    
    async def _analyze_search_results(self, search_results: Dict[str, Any], original_query: str) -> str:
        """Analyze and synthesize search results into a comprehensive response"""
        if not search_results.get("success", False):
            return f"❌ Search failed: {search_results.get('error', 'Unknown error')}"
        
        results = search_results.get("results", [])
        if not results:
            return f"🔍 No relevant documents found for query: '{original_query}'"
        
        # Create comprehensive analysis
        analysis_parts = []
        
        # Summary header with search summary info
        search_summary = search_results.get("search_summary", {})
        analysis_parts.append(f"📊 **Search Results Summary**")
        analysis_parts.append(f"   • Query: '{original_query}'")
        analysis_parts.append(f"   • Found {search_summary.get('total_matches', len(results))} relevant document chunks")
        analysis_parts.append(f"   • Across {search_summary.get('files_found', 'multiple')} unique files")
        analysis_parts.append(f"   • File types: {', '.join(search_summary.get('file_types', []))}")
        analysis_parts.append(f"   • Best relevance score: {search_summary.get('top_similarity', 'N/A')}")
        analysis_parts.append("")
        
        # Process each result with enhanced metadata
        for i, result in enumerate(results[:5], 1):  # Limit to top 5 for detailed analysis
            file_info = result.get('file', result.get('file_info', {}))
            content_info = result.get('content', result.get('content_info', {}))
            timestamps = result.get('timestamps', {})
            
            file_name = file_info.get('name', Path(result.get('source_file', 'Unknown')).name)
            file_path = file_info.get('path', result.get('source_file', 'Unknown'))
            file_size = file_info.get('size', 'Unknown')
            similarity = result.get('similarity_score', 0)
            relevance = result.get('relevance_level', 'Unknown')
            
            analysis_parts.append(f"📄 **Document {i}: {file_name}**")
            analysis_parts.append(f"   • **File**: {file_path}")
            analysis_parts.append(f"   • **Size**: {file_size}")
            analysis_parts.append(f"   • **Type**: {file_info.get('type', 'Unknown')} ({file_info.get('mime_type', 'Unknown')})")
            analysis_parts.append(f"   • **Modified**: {timestamps.get('modified', 'Unknown')}")
            analysis_parts.append(f"   • **Relevance**: {relevance} (score: {similarity:.3f})")
            
            # Chunk information
            chunk_info = content_info.get('chunk_info', f"Chunk {result.get('content_info', {}).get('chunk_index', 0) + 1}")
            analysis_parts.append(f"   • **Chunk**: {chunk_info}")
            
            # Content preview
            content_preview = content_info.get('preview', result.get('content_preview', ''))[:400]
            analysis_parts.append(f"   • **Content**: {content_preview}{'...' if len(content_preview) >= 400 else ''}")
            analysis_parts.append("")
        
        # Additional results summary
        if len(results) > 5:
            analysis_parts.append(f"📋 **Additional Results**: {len(results) - 5} more document chunks found")
            for result in results[5:]:
                file_info = result.get('file', result.get('file_info', {}))
                file_name = file_info.get('name', Path(result.get('source_file', 'Unknown')).name)
                similarity = result.get('similarity_score', 0)
                relevance = result.get('relevance_level', 'Unknown')
                analysis_parts.append(f"   • {file_name} - {relevance} (score: {similarity:.3f})")
            analysis_parts.append("")
        
        # Key insights extraction using enhanced metadata
        analysis_parts.append("🎯 **Key Insights**")
        
        # Extract file types from enhanced metadata
        file_types = set()
        file_sizes = []
        directories = set()
        
        for result in results:
            file_info = result.get('file', result.get('file_info', {}))
            if file_info.get('type'):
                file_types.add(file_info['type'])
            if file_info.get('size_bytes'):
                file_sizes.append(file_info['size_bytes'])
            if file_info.get('directory'):
                directories.add(Path(file_info['directory']).name)
        
        analysis_parts.append(f"   • **Document Types**: {', '.join(file_types) if file_types else 'Various'}")
        analysis_parts.append(f"   • **Source Directories**: {', '.join(directories) if directories else 'Various'}")
        
        if file_sizes:
            avg_size_bytes = sum(file_sizes) / len(file_sizes)
            avg_size_mb = avg_size_bytes / (1024 * 1024)
            analysis_parts.append(f"   • **Average File Size**: {avg_size_mb:.2f} MB")
        
        # Average similarity
        avg_similarity = sum(r.get("similarity_score", 0) for r in results) / len(results)
        analysis_parts.append(f"   • **Average Relevance**: {avg_similarity:.3f}")
        
        analysis_parts.append("")
        analysis_parts.append("💡 **Recommendation**: Use this information as context for further research or analysis.")
        
        return "\n".join(analysis_parts)
    
    async def _generate_query_suggestions(self, original_query: str, search_results: Dict[str, Any]) -> List[str]:
        """Generate follow-up query suggestions based on search results"""
        suggestions = []
        
        if not search_results.get("success", False) or not search_results.get("results", []):
            # Suggest alternative query approaches
            suggestions = [
                f"What documents contain information about {original_query}?",
                f"Find specific details related to {original_query}",
                f"Search for context around {original_query}",
                f"What are the key concepts related to {original_query}?"
            ]
        else:
            # Suggest refinements based on found content using enhanced metadata
            results = search_results["results"]
            
            # Extract key terms from enhanced metadata
            file_types = set()
            file_names = set()
            directories = set()
            
            for result in results:
                file_info = result.get('file', result.get('file_info', {}))
                if file_info.get('type'):
                    file_types.add(file_info['type'])
                if file_info.get('name'):
                    file_names.add(file_info['name'])
                if file_info.get('directory'):
                    directories.add(Path(file_info['directory']).name)
            
            suggestions = []
            
            if file_types:
                suggestions.append(f"Find more details about {original_query} in {list(file_types)[0]} files")
            
            if file_names:
                suggestions.append(f"What else is mentioned in {list(file_names)[0]}?")
            
            if directories:
                suggestions.append(f"Search for {original_query} in {list(directories)[0]} directory")
            
            suggestions.extend([
                f"Find related concepts to {original_query}",
                f"Get comprehensive overview of {original_query} from all sources"
            ])
            
            # Filter out None suggestions and ensure we have some
            suggestions = [s for s in suggestions if s]
            
            if not suggestions:
                suggestions = [
                    f"Find related concepts to {original_query}",
                    f"Get comprehensive overview of {original_query} from all sources"
                ]
        
        return suggestions[:4]  # Return top 4 suggestions
    
    async def _execute_vector_query(self, query: str) -> str:
        """Execute a complete vector query with analysis and suggestions"""
        
        # Check database status first
        db_status = await self._check_vector_database_status()
        if not db_status["available"]:
            return f"❌ Vector Database Error: {db_status['message']}\n\nPlease ensure documents are indexed before querying."
        
        # Perform semantic search
        search_results = await self._perform_semantic_search(query)
        
        # Analyze results
        analysis = await self._analyze_search_results(search_results, query)
        
        # Generate suggestions
        suggestions = await self._generate_query_suggestions(query, search_results)
        
        # Combine into comprehensive response
        response_parts = [analysis]
        
        if suggestions:
            response_parts.append("\n🔍 **Suggested Follow-up Queries:**")
            for i, suggestion in enumerate(suggestions, 1):
                response_parts.append(f"   {i}. {suggestion}")
        
        # Store context for potential follow-ups
        self.current_context = search_results.get("results", [])
        self.processed_queries.append(query)
        
        return "\n".join(response_parts)
    
    async def run(self, task: str) -> str:
        """Main execution method for the Vector Agent"""
        try:
            logger.info(f"Vector Agent starting task: {task}")
            
            # Initialize response
            response_parts = []
            response_parts.append("🔍 **Vector Database Query Agent**")
            response_parts.append("=" * 50)
            response_parts.append("")
            
            # Check if this is a follow-up or related query
            if self.processed_queries:
                response_parts.append(f"📋 Previous queries: {', '.join(self.processed_queries[-3:])}")
                response_parts.append("")
            
            # Execute the vector query
            query_result = await self._execute_vector_query(task)
            response_parts.append(query_result)
            
            # Add final notes
            response_parts.append("")
            response_parts.append("📚 **Notes:**")
            response_parts.append("   • This search was performed on your locally indexed documents")
            response_parts.append("   • Results are ranked by semantic similarity to your query")
            response_parts.append("   • Consider combining this information with web research for comprehensive coverage")
            
            final_response = "\n".join(response_parts)
            
            logger.info(f"Vector Agent completed task with {len(self.current_context)} relevant documents found")
            
            return final_response
            
        except Exception as e:
            error_message = f"❌ Vector Agent Error: {str(e)}"
            logger.error(error_message)
            return f"{error_message}\n\nPlease check the vector database configuration and try again."
    
    def get_current_context(self) -> List[Dict[str, Any]]:
        """Get current document context for use by other agents"""
        return self.current_context
    
    def get_context_summary(self) -> str:
        """Get a summary of current context for other agents"""
        if not self.current_context:
            return "No vector database context available."
        
        summary_parts = []
        summary_parts.append(f"📚 Vector Database Context ({len(self.current_context)} documents):")
        
        for i, doc in enumerate(self.current_context[:3], 1):
            source = Path(doc["source_file"]).name
            score = doc["similarity_score"]
            summary_parts.append(f"   {i}. {source} (relevance: {score:.3f})")
        
        if len(self.current_context) > 3:
            summary_parts.append(f"   ... and {len(self.current_context) - 3} more documents")
        
        return "\n".join(summary_parts) 