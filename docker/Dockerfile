ARG PYTHON_VERSION=3.9

FROM python:${PYTHON_VERSION} as builder

RUN pip3 install mcdreforged

COPY chatbridge /build/chatbridge
COPY lang /build/lang
COPY __main__.py LICENSE mcdreforged.plugin.json requirements.txt /build/
RUN cd /build \
    && mcdreforged pack \
    && find . -name "requirements.txt" -exec cat '{}' \; > requirements.all.txt

FROM python:${PYTHON_VERSION}-slim

COPY --from=builder /build/requirements.all.txt /app/
RUN pip3 install -r /app/requirements.all.txt && pip3 cache purge

COPY --from=builder /build/ChatBridge.pyz /app/
WORKDIR /app
ENTRYPOINT ["python3", "ChatBridge.pyz"]
