from openai import OpenAI
import os, json, logging
import time
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger('operations')
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

assistant_id = "asst_zUXuVBAgp4uFN7VTBHqBW73O"
assistant = client.beta.assistants.retrieve(assistant_id)

def assistant_get_response(thread_id, query_input, query_q=None, file_ids=None, language='en'):
    global assistant
    total_cost_of_query = 0

    if not file_ids:
        message = client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=query_q if query_q else query_input
        )
    else:
        openai_file_ids = get_openai_file_ids(file_ids)
        message = client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=query_q if query_q else query_input,
            attachments=[
                {"file_id": file_id, "tools": [{"type": "file_search"}, {"type": "code_interpreter"}]}
                for file_id in openai_file_ids
            ],
        )

    run = client.beta.threads.runs.create_and_poll(
        thread_id=thread_id,
        assistant_id=assistant.id,
    )

    time.sleep(5)

    if run.status == 'completed':
        messages = client.beta.threads.messages.list(thread_id=thread_id)

        total_cost_of_query += calculate_cost(
            completion_token=run.usage.completion_tokens,
            prompt_token=run.usage.prompt_tokens,
            cached_token=run.usage.prompt_token_details.get('cached_tokens', 0)
        )
        total_cost_of_query *= 4

        if messages.data[0].content[0].text.annotations:
            for annotation in messages.data[0].content[0].text.annotations:
                messages.data[0].content[0].text.value = messages.data[0].content[0].text.value.replace(
                    annotation.text, ''
                )

        return ((messages.data[0].content[0].text.value, total_cost_of_query), "assistant")

    elif run.required_action:
        tool_outputs = []
        for tool in run.required_action.submit_tool_outputs.tool_calls:
            if tool.function.name == "get_response_from_openai_LAW":
                data_dict = json.loads(tool.function.arguments)
                output_from_law = get_response_from_openai_LAW(data_dict['query'])
                total_cost_of_query += output_from_law[1]
                tool_outputs.append({"tool_call_id": tool.id, "output": output_from_law[0]})

            elif tool.function.name == "get_response_from_openai_DECISIONS":
                data_dict = json.loads(tool.function.arguments)
                output_from_decisions = get_response_from_openai_DECISIONS(
                    data_dict['descriptive_query'], data_dict['category']
                )
                total_cost_of_query += output_from_decisions[1]
                tool_outputs.append({"tool_call_id": tool.id, "output": output_from_decisions[0]})

            elif tool.function.name == "get_response_from_Google_CS_API":
                data_dict = json.loads(tool.function.arguments)
                output_from_google = get_response_from_Google_CS_API(
                    data_dict['query'], data_dict['filetype']
                )
                tool_outputs.append({"tool_call_id": tool.id, "output": output_from_google})

        run = client.beta.threads.runs.submit_tool_outputs_and_poll(
            thread_id=thread_id,
            run_id=run.id,
            tool_outputs=tool_outputs
        )

        time.sleep(5)

        if run.status == 'completed':
            messages = client.beta.threads.messages.list(thread_id=thread_id)

            total_cost_of_query += calculate_cost(
                completion_token=run.usage.completion_tokens,
                prompt_token=run.usage.prompt_tokens,
                cached_token=run.usage.prompt_token_details.get('cached_tokens', 0)
            )
            total_cost_of_query *= 4

            return ((str(messages.data[0].content[0].text.value), total_cost_of_query), "RAG")
        else:
            return (("No response from assistant.", 0), "error")

def calculate_cost(completion_token, prompt_token, cached_token=0):
    """Calculate the cost of OpenAI API usage"""
    prompt_cost_per_1k = 0.01
    completion_cost_per_1k = 0.03
    
    prompt_cost = (prompt_token / 1000) * prompt_cost_per_1k
    completion_cost = (completion_token / 1000) * completion_cost_per_1k
    
    return prompt_cost + completion_cost

def get_openai_file_ids(file_ids):
    """Convert file IDs to OpenAI file format"""
    return file_ids if isinstance(file_ids, list) else [file_ids]

def get_response_from_openai_LAW(query):
    """Get response from OpenAI for law-related queries"""
    from .views import SimpleQueryAPI
    api = SimpleQueryAPI()
    try:
        response = api.get_response(query)
        return (response, 0)
    except Exception as e:
        return (f"Error in law query: {str(e)}", 0)

def get_response_from_openai_DECISIONS(descriptive_query, category):
    """Get response from OpenAI for decision-related queries"""
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": f"You are an expert in {category} decisions."},
                {"role": "user", "content": descriptive_query}
            ]
        )
        cost = calculate_cost(
            completion_token=response.usage.completion_tokens,
            prompt_token=response.usage.prompt_tokens
        )
        return (response.choices[0].message.content, cost)
    except Exception as e:
        return (f"Error in decisions query: {str(e)}", 0)

def get_response_from_Google_CS_API(query, filetype):
    """Get response from Google Custom Search API"""
    return f"Google search results for: {query} (filetype: {filetype})"
