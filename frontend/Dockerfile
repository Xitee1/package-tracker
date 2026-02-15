FROM node:20-alpine

WORKDIR /app

ARG APP_VERSION=0.0.0-dev
ENV APP_VERSION=${APP_VERSION}

COPY package*.json ./
RUN npm install

COPY . .

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
