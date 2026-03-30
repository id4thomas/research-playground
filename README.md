# deep-research-demo
Simple Deep Research implemented using LangGraph, traced with mlflow

## Examples
Example notebook is provided as [`examples/streaming-search.ipynb`](./examples/streaming-search.ipynb)

### Streaming Demo Page
![demo](./figs/demo_result.png)

### Tracing Example
![tracing_example](./figs/tracing_mlflow.png)


## Usage
API Server (Runs at port `7100` by default)
```
cp .env.sample .env
# Modify .env

./run-server.sh
```

Gradio Demo Server (Runs at port `7200` by default)
```
./run-demo.sh
```

Streaming Demo Server (Runs at port `7200` by default)
```
./run-stream-demo.sh
```


### API Example
Path: `{API_URL}/search/stream`
```
{
    "query": "{SEARCH_QUERY}",
    "num_topics": 3, # number of topics to fan-out
    "max_attempts": 2, # maximum number of search sub-graph attempts
    "top_k": 5 # final result top-k
}
```

Each event is returned as 3 lines (event + data + empty line)
```
event: {EVENT_TYPE}
data: {EVENT_DATA_JSON}

```

generate_topics node example
```
# Start
event: node_start
data: {"node": "generate_topics"}

# Result
event: node_end
data: {"node": "generate_topics", "topics": ["\uc7...", ...]}

```
