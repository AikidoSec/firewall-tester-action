FROM node:22-slim

# Install git and clone repository in one layer
RUN apt-get update && apt-get install -y git && \
    git clone https://github.com/AikidoSec/firewall-node.git /agent

WORKDIR /agent

# Install dependencies and build in one layer
RUN npm install && \
    npm run build && \
    cd build && \
    npm link

WORKDIR /app

# Copy package files and install dependencies in one layer
COPY package.json ./
RUN npm link @aikidosec/firewall && \
    npm install

# Create app source
COPY app.js ./

EXPOSE 3000

ENV AIKIDO_BLOCK=true \
    AIKIDO_DEBUG=true \
    AIKIDO_ENDPOINT=http://host.docker.internal:3000 \
    AIKIDO_REALTIME_ENDPOINT=http://host.docker.internal:3000

CMD ["node", "app.js"] 