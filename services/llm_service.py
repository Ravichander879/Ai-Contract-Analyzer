import os
import json
import logging
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# We support both the new google-genai and older google-generativeai SDKs for maximum compatibility
try:
    from google import genai
    from google.genai import types
    HAS_NEW_SDK = True
except ImportError:
    import google.generativeai as genai
    HAS_NEW_SDK = False

from prompts.templates import (
    ANALYSIS_SYSTEM_PROMPT,
    ANALYSIS_USER_PROMPT,
    CHAT_SYSTEM_PROMPT,
    CHAT_USER_PROMPT
)

load_dotenv()

logger = logging.getLogger(__name__)

def clean_json_string(raw_text: str) -> str:
    """
    Cleans markdown code blocks (e.g. ```json ... ```) from raw LLM responses.
    """
    text = raw_text.strip()
    if text.startswith("```"):
        # Remove opening fence
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        # Remove closing fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text

def get_gemini_client(api_key: Optional[str] = None):
    """
    Instantiates and returns the configured Gemini client/SDK.
    """
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        raise ValueError("GEMINI_API_KEY is not configured. Please set it in .env or provide it in the input field.")
    return key

def analyze_contract_text(contract_text: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Analyzes contract text using Gemini, requesting structured JSON output.
    """
    key = get_gemini_client(api_key)
    model_name = "gemini-2.5-flash"
    
    prompt = ANALYSIS_USER_PROMPT.format(contract_text=contract_text)
    
    try:
        if HAS_NEW_SDK:
            client = genai.Client(api_key=key)
            # Use gemini-2.5-flash with structured JSON response
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=ANALYSIS_SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )
            raw_text = response.text
        else:
            genai.configure(api_key=key)
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=ANALYSIS_SYSTEM_PROMPT
            )
            response = model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json", "temperature": 0.1}
            )
            raw_text = response.text
            
        cleaned_json = clean_json_string(raw_text)
        analysis_data = json.loads(cleaned_json)
        return analysis_data
        
    except Exception as e:
        logger.error(f"Error calling Gemini API for analysis: {str(e)}")
        # Try a fallback without structured JSON config in case model/SDK version doesn't support it
        try:
            if HAS_NEW_SDK:
                client = genai.Client(api_key=key)
                response = client.models.generate_content(
                    model="gemini-1.5-flash",
                    contents=f"{ANALYSIS_SYSTEM_PROMPT}\n\n{prompt}"
                )
                raw_text = response.text
            else:
                genai.configure(api_key=key)
                model = genai.GenerativeModel("gemini-1.5-flash")
                response = model.generate_content(f"{ANALYSIS_SYSTEM_PROMPT}\n\n{prompt}")
                raw_text = response.text
                
            cleaned_json = clean_json_string(raw_text)
            analysis_data = json.loads(cleaned_json)
            return analysis_data
        except Exception as e_fallback:
            logger.error(f"Fallback Gemini API call failed: {str(e_fallback)}")
            raise RuntimeError(f"Gemini API analysis failed: {str(e_fallback)}")

def chat_with_contract(
    question: str, 
    context_chunks: List[Dict[str, Any]], 
    api_key: Optional[str] = None
) -> str:
    """
    Answers a question about the contract based on retrieved FAISS chunks.
    """
    key = get_gemini_client(api_key)
    model_name = "gemini-2.5-flash"
    
    # Format the context blocks
    context_str = ""
    for idx, chunk in enumerate(context_chunks):
        context_str += f"Block {idx+1} (Page {chunk['page_num']}):\n{chunk['text']}\n\n"
        
    user_prompt = CHAT_USER_PROMPT.format(question=question, context_blocks=context_str)
    
    try:
        if HAS_NEW_SDK:
            client = genai.Client(api_key=key)
            response = client.models.generate_content(
                model=model_name,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=CHAT_SYSTEM_PROMPT,
                    temperature=0.2
                )
            )
            return response.text
        else:
            genai.configure(api_key=key)
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=CHAT_SYSTEM_PROMPT
            )
            response = model.generate_content(user_prompt)
            return response.text
    except Exception as e:
        logger.error(f"Error calling Gemini API for chat: {str(e)}")
        # Try fallback model
        try:
            if HAS_NEW_SDK:
                client = genai.Client(api_key=key)
                response = client.models.generate_content(
                    model="gemini-1.5-flash",
                    contents=f"{CHAT_SYSTEM_PROMPT}\n\n{user_prompt}"
                )
                return response.text
            else:
                genai.configure(api_key=key)
                model = genai.GenerativeModel("gemini-1.5-flash")
                response = model.generate_content(f"{CHAT_SYSTEM_PROMPT}\n\n{user_prompt}")
                return response.text
        except Exception as e_fallback:
            logger.error(f"Fallback Gemini chat failed: {str(e_fallback)}")
            return f"Error communicating with Gemini: {str(e_fallback)}"
