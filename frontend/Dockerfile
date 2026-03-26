FROM node:20-alpine

WORKDIR /app

ARG APP_VERSION=0.0.0-dev
ARG REPO_URL=https://github.com/Xitee1/package-tracker
ENV APP_VERSION=${APP_VERSION}
ENV REPO_URL=${REPO_URL}

COPY package*.json ./
RUN npm install

COPY . .

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
