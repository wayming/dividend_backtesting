FROM python:3.12-slim

ARG DEV_UID=1000
ARG DEV_GID=1000

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    bash \
    unzip \
    ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*


RUN if getent passwd 1000; then userdel -f $(getent passwd 1000 | cut -d: -f1); fi \
    && if getent group 1000; then groupdel $(getent group 1000 | cut -d: -f1) || true; fi

RUN groupadd -g ${DEV_GID} dev \
    && useradd -m -u ${DEV_UID} -g dev -s /bin/bash -d /home/dev dev \
    && mkdir -p /workspace \
    && chown -R dev:dev /workspace /home/dev
USER dev
WORKDIR /workspace

ENV NPM_CONFIG_PREFIX=/home/dev/.npm-global
ENV PATH=/home/dev/.npm-global/bin:/home/dev/.local/bin:$PATH
# ENV CLAUDE_CONFIG_DIR=/workspace/claude_config

RUN npm install -g @anthropic-ai/claude-code

CMD ["tail", "-f", "/dev/null"]