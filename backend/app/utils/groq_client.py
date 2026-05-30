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
    repo_name: str
) -> tuple[str, list[str]]:

    try:
        code_snippet = ""
        if raw_code:
            code_snippet = raw_code[:1500]

        prompt = f"""You are analyzing source code for a project called {repo_name}.

Analyze this {node_type} named '{node_name}':
File: {full_path}
Signature: {signature or 'not available'}
Code:
{code_snippet or 'not available'}

Respond with ONLY a JSON object, no markdown, 
no explanation, no code blocks:
{{"summary": "One clear sentence describing what this code does and its purpose", "tags": ["tag1", "tag2", "tag3"]}}

Tags must be 2-5 lowercase technical keywords
such as: authentication, database, validation,
payment, async, crud, api, middleware, util,
parsing, caching, routing, error-handling."""

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
