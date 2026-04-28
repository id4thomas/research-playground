# PP-doclayout tritonserver
## Usage
1. Build venv tar file (venv-builder)
2. Define `.env` file
3. Run tritonserver
4. test inference

### 1. Build venv tar file
- build-env will build venv builder docker image & run conda-pack inside a container
- `env.tar.gz` file will be created in the directory

```
cd venv-builder
./build-env.sh
```

### 2. Define `.env` file
Copy `.env.example` to `.env` and set values.
```
WEIGHTS_DIR=/absolute/path/to/PP-DocLayoutV3_safetensors
DOCLAYOUT_THRESHOLD=0.5

# Host ports mapped to Triton's 8000 (HTTP), 8001 (gRPC), 8002 (metrics)
TRITON_HTTP_PORT=8000
TRITON_GRPC_PORT=8001
TRITON_METRICS_PORT=8002
```

### 3. Run tritonserver
Run official nvidia tritonserver image with following files mounted
- Model Registry: model.py code & config.pbtxt
- Model Weights: doc-layout safetensor weights (`model.py` looks for them in `/model`)
- Venv Conda-Pack Tar: `config.pbtxt` defines the location as `/opt/env.tar.gz`

```
./run-server.sh
```

Running the server will expose 3 ports (host ports set in `.env`, defaults shown):
- 8000: HTTP inference API
- 8001: gRPC inference API
- 8002: Prometheus metrics

### 4. Test Inference
`test_server.py` sends an image to the HTTP endpoint and prints the returned layout items.

```
# default host/port (localhost:8000)
python test_server.py page.jpeg

# custom port (matches TRITON_HTTP_PORT in .env)
python test_server.py page.jpeg --port 6000

# custom host + port
python test_server.py page.jpeg --host 192.168.1.10 --port 6000

# multiple images
python test_server.py page1.jpeg page2.jpeg --port 6000
```


## Venv Builder
tritonserver accepts custom python venv as conda-pack tar files.

**Requirements**
- use opencv-python-headless to prevent "libGL.so not found" issues