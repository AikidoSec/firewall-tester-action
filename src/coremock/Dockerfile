ARG CORE_BASE_IMAGE=node:20-alpine
FROM ${CORE_BASE_IMAGE}

WORKDIR /app

COPY package.json package-lock.json tsconfig.json tsconfig.base.json ./
COPY src ./src

RUN npm ci

EXPOSE 3000

ENTRYPOINT npm run start-core
