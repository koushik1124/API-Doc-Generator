import os
import json
import re
import logging
from typing import Dict, List
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMClient:
    """
    LLM client for generating code documentation with robust JSON parsing.
    """
    
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        
        self.client = Groq(api_key=api_key)
        self.model = "llama-3.3-70b-versatile"
        logger.info("✅ LLM Client initialized")
    
    def generate_docs(self, function_info: Dict, context: List[str] = None) -> Dict:
        """
        Generate documentation for a function with RAG context.
        
        Args:
            function_info: Dict with 'name', 'args', 'docstring', 'source'
            context: List of relevant context strings from RAG
            
        Returns:
            Dict with structured documentation
        """
        try:
            prompt = self._build_prompt(function_info, context)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a code documentation expert. Always respond with ONLY valid JSON, no markdown formatting, no code blocks, no backticks."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            raw_content = response.choices[0].message.content
            logger.debug(f"Raw LLM response: {raw_content[:200]}...")
            
            # Clean and parse JSON
            parsed = self._parse_llm_response(raw_content)
            
            return parsed
            
        except Exception as e:
            logger.error(f"Failed to generate docs: {e}")
            return {
                "error": str(e),
                "raw": raw_content if 'raw_content' in locals() else "No response"
            }
    
    def _build_prompt(self, function_info: Dict, context: List[str] = None) -> str:
        """
        Build prompt for documentation generation.
        """
        func_name = function_info.get('name', 'unknown')
        params = function_info.get('args', [])
        docstring = function_info.get('docstring', '')
        source = function_info.get('source', '')
        returns = function_info.get('returns', None)
        
        # Build context section
        context_str = ""
        if context and len(context) > 0:
            context_str = "\n\nRELEVANT CODEBASE CONTEXT:\n"
            context_str += "\n".join([f"- {c[:200]}" for c in context[:3]])
        
        prompt = f"""Generate documentation for this Python function. Return ONLY a JSON object with NO markdown formatting, NO code blocks, NO backticks.

FUNCTION TO DOCUMENT:
Name: {func_name}
Parameters: {', '.join(params) if params else 'None'}
Return Type: {returns if returns else 'Not specified'}
Existing Docstring: {docstring if docstring else 'None'}

SOURCE CODE:
{source}
{context_str}

Return ONLY this exact JSON structure with no extra formatting:
{{
  "description": "Brief 1-2 sentence explanation of what the function does",
  "parameters": ["param1: explanation", "param2: explanation"],
  "returns": "What the function returns",
  "example": "function_name(arg1, arg2)",
  "notes": "Any additional important details or edge cases"
}}

CRITICAL: Return ONLY the JSON object above. Do NOT wrap it in ```json or ``` or any markdown. Just the raw JSON."""

        return prompt
    
    def _parse_llm_response(self, response: str) -> Dict:
        """
        Parse LLM response with robust cleaning to extract JSON.
        Handles markdown code blocks, extra text, and malformed JSON.
        """
        if not response or not response.strip():
            raise ValueError("Empty response from LLM")
        
        # Clean the response
        cleaned = self._clean_json_response(response)
        
        try:
            # Try to parse as JSON
            parsed = json.loads(cleaned)
            
            # Validate structure
            if not isinstance(parsed, dict):
                raise ValueError("Response is not a JSON object")
            
            # Ensure required fields exist with defaults
            result = {
                "description": parsed.get("description", "No description provided"),
                "parameters": parsed.get("parameters", []),
                "returns": parsed.get("returns", "Not specified"),
                "example": parsed.get("example", ""),
                "notes": parsed.get("notes", "")
            }
            
            logger.info("✅ Successfully parsed JSON response")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
            logger.error(f"Cleaned response: {cleaned[:500]}")
            
            # Return error with the cleaned response for debugging
            return {
                "error": "LLM returned invalid JSON structure",
                "raw": response[:500],
                "cleaned": cleaned[:500]
            }
    
    def _clean_json_response(self, response: str) -> str:
        """
        Clean LLM response to extract pure JSON.
        Removes markdown code blocks, extra text, and formatting.
        """
        # Remove leading/trailing whitespace
        cleaned = response.strip()
        
        # Remove markdown code blocks: ```json ... ```
        cleaned = re.sub(r'^```json\s*', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'^```\s*', '', cleaned)
        cleaned = re.sub(r'\s*```$', '', cleaned)
        
        # Remove any text before first {
        first_brace = cleaned.find('{')
        if first_brace > 0:
            cleaned = cleaned[first_brace:]
        
        # Remove any text after last }
        last_brace = cleaned.rfind('}')
        if last_brace > 0:
            cleaned = cleaned[:last_brace + 1]
        
        # Fix common JSON issues
        # Replace single quotes with double quotes (if not inside strings)
        # This is risky but helps with malformed JSON
        
        # Remove trailing commas before } or ]
        cleaned = re.sub(r',(\s*[}\]])', r'\1', cleaned)
        
        return cleaned.strip()
    
    def generate_docs_batch(self, functions: List[Dict], contexts: List[List[str]]) -> List[Dict]:
        """
        Generate documentation for multiple functions.
        
        Args:
            functions: List of function info dicts
            contexts: List of context lists (one per function)
            
        Returns:
            List of documentation dicts
        """
        results = []
        
        for i, func in enumerate(functions):
            context = contexts[i] if i < len(contexts) else []
            doc = self.generate_docs(func, context)
            results.append(doc)
        
        return results
    
    def test_connection(self) -> bool:
        """
        Test if LLM connection is working.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Say 'OK'"}],
                max_tokens=10
            )
            return bool(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False


# Backward compatibility
def generate_documentation(func_info: dict, context: list = None) -> str:
    """Legacy function for backward compatibility"""
    client = LLMClient()
    return client.generate_docs(func_info, context)