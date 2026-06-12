from groq import Groq
import json
import asyncio
from app.config import get_settings

settings = get_settings()

# Initialize Groq client
groq_client = Groq(api_key=settings.groq_api_key)

async def generate_node_summary(
    node_name: str,
    node_type: str,
    full_path: str,
    signature: str | None,
    raw_code: str | None,
    repo_name: str,
    repo_description: str | None = None,
    repo_language: str | None = None,
    imports: list[str] | None = None,
    calls: list[str] | None = None,
    called_by: list[str] | None = None,
    existing_summary: str | None = None,
) -> dict:

    try:
        code_snippet = ""
        if raw_code:
            code_snippet = raw_code[:2500]

        prompt = f"""You are a Senior Staff Software Engineer performing a deep architecture review.

Repository: {repo_name}
Repository Description: {repo_description or 'N/A'}
Repository Primary Language: {repo_language or 'N/A'}

File: {full_path}
Node Type: {node_type}
Node Name: {node_name}
Signature: {signature or 'not available'}
"""

        if imports:
            prompt += f"Imports: {', '.join(imports)}\n"
        else:
            prompt += "Imports: none\n"

        if calls:
            prompt += f"Calls: {', '.join(calls)}\n"
        else:
            prompt += "Calls: none\n"

        if called_by:
            prompt += f"Called By: {', '.join(called_by)}\n"
        else:
            prompt += "Called By: none\n"

        if existing_summary:
            prompt += f"Existing Summary: {existing_summary}\n"

        prompt += f"""
Code:
{code_snippet or 'not available'}

Respond with ONLY a JSON object, no markdown, no explanation, no code fences.
The JSON must contain the following keys:
- summary
- detailed_explanation
- responsibilities
- inputs
- outputs
- dependencies
- architecture_role
- call_flow
- call_flow_diagram
- potential_risks
- related_components
- complexity_level
- tags
- ai_tags

The call_flow_diagram must be Mermaid-compatible text, starting with `graph TD`.
For arrays, return a JSON list of short descriptive strings.
For complexity_level return one of: Low, Medium, High, or Critical.
For tags and ai_tags return lowercase technical keywords.
Example response:
{"summary": "...", "detailed_explanation": "...", "responsibilities": ["..."], "inputs": ["..."], "outputs": ["..."], "dependencies": ["..."], "architecture_role": "...", "call_flow": ["..."], "call_flow_diagram": "graph TD\nA[API] --> B[Service]", "potential_risks": ["..."], "related_components": ["..."], "complexity_level": "Medium", "tags": ["api", "security"], "ai_tags": ["architecture", "scalability"]}
"""

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=600,
                temperature=0.1,
            )
        )

        text = response.choices[0].message.content.strip()

        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        text = text.strip()

        if not text.startswith("{"):
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                text = text[start:end+1]

        data = json.loads(text)

        return {
            "summary": str(data.get("summary", "Summary not available")),
            "detailed_explanation": str(data.get("detailed_explanation", "")),
            "responsibilities": [str(item) for item in data.get("responsibilities", []) if item],
            "inputs": [str(item) for item in data.get("inputs", []) if item],
            "outputs": [str(item) for item in data.get("outputs", []) if item],
            "dependencies": [str(item) for item in data.get("dependencies", []) if item],
            "architecture_role": str(data.get("architecture_role", "")),
            "call_flow": [str(item) for item in data.get("call_flow", []) if item],
            "call_flow_diagram": str(data.get("call_flow_diagram", "")),
            "potential_risks": [str(item) for item in data.get("potential_risks", []) if item],
            "related_components": [str(item) for item in data.get("related_components", []) if item],
            "complexity_level": str(data.get("complexity_level", "Medium")),
            "tags": [str(item).lower() for item in data.get("tags", []) if item],
            "ai_tags": [str(item).lower() for item in data.get("ai_tags", []) if item],
        }

    except Exception as e:
        print(f"Groq error for {node_name}: {e}")
        return {
            "summary": "Summary not available",
            "detailed_explanation": "",
            "responsibilities": [],
            "inputs": [],
            "outputs": [],
            "dependencies": [],
            "architecture_role": "",
            "call_flow": [],
            "call_flow_diagram": "",
            "potential_risks": [],
            "related_components": [],
            "complexity_level": "Medium",
            "tags": [],
            "ai_tags": [],
        }

        # Call synchronously in threadpool since client.chat.completions.create is blocking
        # but the function itself is async.
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.1,
            )
        )

        text = response.choices[0].message.content.strip()
        
        # Clean response — remove markdown if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        text = text.strip()

        data = json.loads(text)
        summary = data.get("summary", "")
        tags = data.get("tags", [])

        if not isinstance(tags, list):
            tags = []
        tags = [str(t).lower() for t in tags[:5]]

        return summary, tags

    except Exception as e:
        print(f"Groq error for {node_name}: {e}")
        return "Summary not available", []
