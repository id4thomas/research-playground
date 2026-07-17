import os

import gradio as gr
import httpx

API_URL = os.environ.get("API_URL", "http://localhost:7100/search")


async def search(query, num_topics, max_attempts, top_k):
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(API_URL, json={
            "query": query,
            "num_topics": num_topics,
            "max_attempts": max_attempts,
            "top_k": top_k,
        })
        response.raise_for_status()
        data = response.json()

    topics = data.get("topics", [])
    papers = data.get("papers", [])

    topics_md = "\n".join(f"- {t}" for t in topics)

    papers_md = ""
    for i, p in enumerate(papers, 1):
        score = p.get("relevance_score", 0)
        title = p.get("title", "")
        authors = ", ".join(p.get("authors", [])[:3])
        summary = p.get("summary", "")[:200]
        paper_id = p.get("id", "")
        link = f"https://huggingface.co/papers/{paper_id}" if paper_id else ""

        papers_md += f"### {i}. [{title}]({link})\n"
        papers_md += f"**Score:** {score:.2f} | **Authors:** {authors}\n\n"
        papers_md += f"{summary}...\n\n---\n\n"

    return f"## Topics\n{topics_md}\n\n## Papers ({len(papers)})\n\n{papers_md}"


with gr.Blocks(title="Deep Research") as demo:
    gr.Markdown("# Deep Research Paper Search")

    with gr.Row():
        with gr.Column(scale=2):
            query_input = gr.Textbox(label="Research Query", placeholder="e.g. medical graph rag", lines=3)
            num_topics = gr.Slider(1, 5, value=3, step=1, label="Num Topics")
            max_attempts = gr.Slider(1, 5, value=2, step=1, label="Max Attempts")
            top_k = gr.Slider(1, 20, value=10, step=1, label="Top K")
            search_btn = gr.Button("Search", variant="primary")

        with gr.Column(scale=8):
            output = gr.Markdown(label="Results", value="Results will appear here.")

    search_btn.click(
        fn=search,
        inputs=[query_input, num_topics, max_attempts, top_k],
        outputs=output,
        show_progress=True,
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
