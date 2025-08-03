import asyncio
from typing import Dict, List, Any, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor
import time

from src.tools import AsyncTool, ToolResult
from src.tools.vector_database import VectorSearchTool
from src.tools.deep_researcher import DeepResearcherTool
from src.registry import TOOL
from src.logger import logger

# @TOOL.register_module(name="parallel_research_tool", force=True)  # Disabled - parallel execution is now automatic
class ParallelResearchTool(AsyncTool):
    """
    Advanced tool for coordinating parallel execution of vector database search and web research.
    
    This tool optimizes research latency by running vector search and web research simultaneously,
    then combining the results for comprehensive analysis.
    """
    
    name = "parallel_research_tool"
    description = "Execute vector database search and web research in parallel for optimal latency and comprehensive coverage."
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The research query to search for in both vector database and web sources"
            },
            "vector_max_results": {
                "type": "integer",
                "description": "Maximum number of results from vector database search (default: 5)",
                "default": 5,
                "nullable": True
            },
            "web_research_depth": {
                "type": "string", 
                "description": "Depth of web research: 'quick', 'standard', 'comprehensive' (default: 'standard')",
                "default": "standard",
                "nullable": True
            },
            "include_analysis": {
                "type": "boolean",
                "description": "Whether to include cross-source analysis and synthesis (default: True)",
                "default": True,
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
        
        # Initialize component tools
        self.vector_search_tool = VectorSearchTool(
            db_path=db_path,
            embeddings_model=embeddings_model
        )
        self.web_research_tool = DeepResearcherTool()
        
        # Performance tracking
        self.execution_stats = {
            "parallel_executions": 0,
            "avg_vector_time": 0.0,
            "avg_web_time": 0.0,
            "avg_total_time": 0.0
        }
    
    async def _execute_vector_search(self, query: str, max_results: int = 5) -> Tuple[Dict[str, Any], float]:
        """Execute vector database search with timing"""
        start_time = time.time()
        
        try:
            result = await self.vector_search_tool.forward(query, max_results=max_results)
            execution_time = time.time() - start_time
            
            if result.error:
                return {
                    "success": False,
                    "error": result.error,
                    "source": "vector_database",
                    "execution_time": execution_time
                }, execution_time
            
            return {
                "success": True,
                "source": "vector_database",
                "query": query,
                "results": result.output,
                "execution_time": execution_time
            }, execution_time
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Vector search failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "source": "vector_database",
                "execution_time": execution_time
            }, execution_time
    
    async def _execute_web_research(self, query: str, depth: str = "standard") -> Tuple[Dict[str, Any], float]:
        """Execute web research with timing"""
        start_time = time.time()
        
        try:
            # Adjust research parameters based on depth
            research_params = {
                "quick": {"max_insights": 10, "time_limit_seconds": 30},
                "standard": {"max_insights": 20, "time_limit_seconds": 60}, 
                "comprehensive": {"max_insights": 30, "time_limit_seconds": 120}
            }
            
            params = research_params.get(depth, research_params["standard"])
            
            result = await self.web_research_tool.forward(query)
            execution_time = time.time() - start_time
            
            if result.error:
                return {
                    "success": False,
                    "error": result.error,
                    "source": "web_research",
                    "execution_time": execution_time
                }, execution_time
            
            return {
                "success": True,
                "source": "web_research",
                "query": query,
                "results": result.output,
                "execution_time": execution_time
            }, execution_time
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Web research failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "source": "web_research", 
                "execution_time": execution_time
            }, execution_time
    
    def _analyze_combined_results(self, vector_results: Dict[str, Any], web_results: Dict[str, Any], original_query: str) -> Dict[str, Any]:
        """Analyze and synthesize results from both sources"""
        analysis = {
            "query": original_query,
            "sources_analyzed": [],
            "key_findings": {},
            "cross_validation": {},
            "coverage_analysis": {},
            "recommendations": []
        }
        
        # Analyze vector database results
        if vector_results.get("success", False):
            analysis["sources_analyzed"].append("vector_database")
            vector_data = vector_results.get("results", {})
            
            analysis["key_findings"]["vector_database"] = {
                "results_count": vector_data.get("results_count", 0),
                "documents_found": len(vector_data.get("results", [])),
                "top_sources": [
                    result.get("source_file", "Unknown") 
                    for result in vector_data.get("results", [])[:3]
                ],
                "avg_relevance": self._calculate_avg_relevance(vector_data.get("results", []))
            }
        
        # Analyze web research results
        if web_results.get("success", False):
            analysis["sources_analyzed"].append("web_research")
            web_data = web_results.get("results", "")
            
            analysis["key_findings"]["web_research"] = {
                "content_length": len(str(web_data)),
                "research_scope": "comprehensive_web_search",
                "external_sources": "multiple_web_sources"
            }
        
        # Cross-validation analysis
        if len(analysis["sources_analyzed"]) > 1:
            analysis["cross_validation"] = {
                "sources_available": analysis["sources_analyzed"],
                "complementary_coverage": True,
                "internal_external_balance": "optimal"
            }
        
        # Coverage analysis
        analysis["coverage_analysis"] = {
            "internal_knowledge": "vector_database" in analysis["sources_analyzed"],
            "external_knowledge": "web_research" in analysis["sources_analyzed"],
            "comprehensive_coverage": len(analysis["sources_analyzed"]) >= 2,
            "research_quality": "high" if len(analysis["sources_analyzed"]) >= 2 else "moderate"
        }
        
        # Generate recommendations
        if "vector_database" in analysis["sources_analyzed"] and "web_research" in analysis["sources_analyzed"]:
            analysis["recommendations"] = [
                "Excellent coverage: Both internal documents and external sources analyzed",
                "Cross-reference findings between vector database and web research",
                "Leverage internal knowledge as foundation, external knowledge for validation",
                "Consider follow-up research for any identified gaps"
            ]
        elif "vector_database" in analysis["sources_analyzed"]:
            analysis["recommendations"] = [
                "Internal documents analyzed successfully",
                "Consider web research for external validation and current information",
                "Leverage internal knowledge for specific context and details"
            ]
        elif "web_research" in analysis["sources_analyzed"]:
            analysis["recommendations"] = [
                "External web research completed successfully", 
                "Consider indexing relevant documents for future internal reference",
                "Leverage external knowledge for current and comprehensive coverage"
            ]
        else:
            analysis["recommendations"] = [
                "No successful research results obtained",
                "Check vector database availability and web connectivity",
                "Consider alternative research approaches or query refinement"
            ]
        
        return analysis
    
    def _calculate_avg_relevance(self, results: List[Dict[str, Any]]) -> float:
        """Calculate average relevance score from vector search results"""
        if not results:
            return 0.0
        
        relevance_scores = [
            result.get("similarity_score", 0.0) 
            for result in results 
            if "similarity_score" in result
        ]
        
        return sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.0
    
    def _update_performance_stats(self, vector_time: float, web_time: float, total_time: float):
        """Update performance tracking statistics"""
        self.execution_stats["parallel_executions"] += 1
        count = self.execution_stats["parallel_executions"]
        
        # Calculate running averages
        self.execution_stats["avg_vector_time"] = (
            (self.execution_stats["avg_vector_time"] * (count - 1) + vector_time) / count
        )
        self.execution_stats["avg_web_time"] = (
            (self.execution_stats["avg_web_time"] * (count - 1) + web_time) / count
        )
        self.execution_stats["avg_total_time"] = (
            (self.execution_stats["avg_total_time"] * (count - 1) + total_time) / count
        )
    
    async def forward(self, 
                     query: str, 
                     vector_max_results: int = 5,
                     web_research_depth: str = "standard",
                     include_analysis: bool = True) -> ToolResult:
        """Execute parallel research across vector database and web sources"""
        
        start_time = time.time()
        
        try:
            logger.info(f"Starting parallel research for query: '{query}'")
            
            # Execute vector search and web research in parallel
            vector_task = self._execute_vector_search(query, vector_max_results)
            web_task = self._execute_web_research(query, web_research_depth)
            
            # Wait for both tasks to complete
            (vector_results, vector_time), (web_results, web_time) = await asyncio.gather(
                vector_task, web_task, return_exceptions=False
            )
            
            total_time = time.time() - start_time
            
            # Update performance statistics
            self._update_performance_stats(vector_time, web_time, total_time)
            
            # Build comprehensive response
            response = {
                "parallel_research_results": {
                    "query": query,
                    "execution_summary": {
                        "total_time": total_time,
                        "vector_time": vector_time,
                        "web_time": web_time,
                        "parallel_efficiency": max(vector_time, web_time) / total_time,
                        "latency_optimization": f"{((vector_time + web_time) - total_time):.2f}s saved"
                    },
                    "vector_database_results": vector_results,
                    "web_research_results": web_results
                }
            }
            
            # Add cross-source analysis if requested
            if include_analysis:
                response["parallel_research_results"]["combined_analysis"] = self._analyze_combined_results(
                    vector_results, web_results, query
                )
            
            # Add performance insights
            response["parallel_research_results"]["performance_insights"] = {
                "current_execution": {
                    "sources_successful": sum([
                        vector_results.get("success", False),
                        web_results.get("success", False)
                    ]),
                    "parallel_efficiency": f"{(max(vector_time, web_time) / total_time * 100):.1f}%",
                    "time_saved": f"{(vector_time + web_time) - total_time:.2f}s"
                },
                "historical_performance": self.execution_stats
            }
            
            logger.info(f"Parallel research completed in {total_time:.2f}s (Vector: {vector_time:.2f}s, Web: {web_time:.2f}s)")
            
            return ToolResult(output=response, error=None)
            
        except Exception as e:
            total_time = time.time() - start_time
            error_msg = f"Parallel research failed: {str(e)}"
            logger.error(error_msg)
            
            return ToolResult(
                output={
                    "parallel_research_results": {
                        "query": query,
                        "error": error_msg,
                        "execution_time": total_time
                    }
                },
                error=error_msg
            ) 