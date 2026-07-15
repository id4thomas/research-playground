import os

import gradio as gr
import httpx

API_URL = os.environ.get("API_URL", "http://localhost:7100/search")


async def search(topic, search_limit, min_required, max_iteration, score_threshold):
    async with httpx.AsyncClient(timeout=300) as client:
        response = await client.post(API_URL, json={
            "topic": topic,
            "search_limit": int(search_limit),
            "min_required": int(min_required),
            "max_iteration": int(max_iteration),
            "score_threshold": score_threshold,
        })
        response.raise_for_status()
        data = response.json()

    iteration = data.get("iteration", 0)
    papers = data.get("papers", [])

    papers_md = ""
    for i, p in enumerate(papers, 1):
        score = p.get("score", 0)
        title = p.get("title", "")
        authors = ", ".join(p.get("authors", [])[:3])
        summary = p.get("summary", "")[:200]
        source_query = p.get("source_query", "")
        paper_id = p.get("id", "")
        link = f"https://huggingface.co/papers/{paper_id}" if paper_id else ""

        papers_md += f"### {i}. [{title}]({link})\n"
        papers_md += f"**Score:** {score:.2f} | **Query:** {source_query} | **Authors:** {authors}\n\n"
        papers_md += f"{summary}...\n\n---\n\n"

    return f"## Papers ({len(papers)}) — {iteration} iteration(s)\n\n{papers_md}"


with gr.Blocks(title="HF Paper Search") as demo:
    gr.Markdown("# HF Paper Search")

    with gr.Row():
        with gr.Column(scale=2):
            topic_input = gr.Textbox(label="Topic", placeholder="e.g. medical graph rag", lines=3)
            search_limit = gr.Slider(1, 20, value=10, step=1, label="Search Limit")
            min_required = gr.Slider(1, 10, value=3, step=1, label="Min Required")
            max_iteration = gr.Slider(1, 5, value=2, step=1, label="Max Iteration")
            score_threshold = gr.Slider(0.0, 1.0, value=0.5, step=0.05, label="Score Threshold")
            search_btn = gr.Button("Search", variant="primary")

        with gr.Column(scale=8):
            output = gr.Markdown(label="Results", value="Results will appear here.")

    search_btn.click(
        fn=search,
        inputs=[topic_input, search_limit, min_required, max_iteration, score_threshold],
        outputs=output,
        show_progress=True,
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
