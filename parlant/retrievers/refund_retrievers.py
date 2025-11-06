
import os

import parlant.sdk as p


@p.retriever
async def get_refund_context(context: p.RetrieverContext) -> p.RetrieverResult:
    """
    Retrieves the content of a specified context file.

    Args:
        file_name (str): The name of the file to retrieve from the processed context directory.
    """
    file_name = context.inputs.get("file_name")
    processed_context_dir = os.path.join(os.path.dirname(__file__), "context", "processed")
    file_path = os.path.join(processed_context_dir, file_name)

    try:
        with open(file_path, "r") as f:
            content = f.read()
        return p.RetrieverResult(result=content, summary=f"Retrieved content from {file_name}")
    except FileNotFoundError:
        return p.RetrieverResult(result=None, summary=f"File not found: {file_name}")
