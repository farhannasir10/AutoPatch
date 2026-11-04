FROM node:20-slim
WORKDIR /workspace

# bake the cart sample deps so the sandbox can stay network-disabled
COPY package.json ./
RUN npm install --no-fund --no-audit

# source files get overlaid at runtime via put_archive
