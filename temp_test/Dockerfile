FROM node:22-slim

RUN apt-get update && apt-get install -y git

RUN git clone https://github.com/AikidoSec/firewall-node.git /agent

WORKDIR /agent
RUN npm install

WORKDIR /agent/library

# (Probably not needed)
RUN npm install

# Build the firewall library (this creates the build/ directory)
WORKDIR /agent
RUN npm run build

# Make the built package available globally via npm link
WORKDIR /agent/build
RUN npm link

WORKDIR /agent

# Expose the build directory for extending images
VOLUME ["/agent/build"] 


WORKDIR /app

COPY package.json ./

# Link the dev build of the firewall
RUN npm link @aikidosec/firewall

# Install app dependencies
RUN npm install

# Create app source
COPY app.js ./

EXPOSE 3000

ENV AIKIDO_BLOCK=true
ENV AIKIDO_DEBUG=true
#ENV AIKIDO_TOKEN=
ENV AIKIDO_ENDPOINT=http://host.docker.internal:3000
ENV AIKIDO_REALTIME_ENDPOINT=http://host.docker.internal:3000

CMD ["node", "app.js"] 