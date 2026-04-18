FROM continuumio/miniconda3:26.1.1

ENV PYTHONNOUSERSITE=True
ENV PATH="/opt/conda/bin:${PATH}"

# Python version must match the python_backend stub in tritonserver:26.01-py3.
# libxcb / libglvnd are runtime deps of some image libs (cv2 etc.) and are
# bundled via conda so they ship inside the packed env.
# tritonserver:26.03-py3 uses 3.12
RUN conda create -y -n triton_env --override-channels -c conda-forge python=3.12 && \
    conda install -y -n triton_env --override-channels -c conda-forge \
      conda-pack libxcb libglvnd

# At runtime: /tmp/requirements.txt is mounted; output is written to /tmp/venv.tar.gz.
CMD conda run -n triton_env pip install --no-cache-dir -r /tmp/requirements.txt && \
    conda run -n triton_env conda-pack -n triton_env -o /tmp/venv.tar.gz \
      --ignore-editable-packages --ignore-missing-files
