FROM node:16.13.1

WORKDIR /usr/src/app
COPY package*.json ./
RUN npm install --only=production
COPY ./src ./src
EXPOSE 3000
CMD npm start

# docker run --env-file ./.env -p 3000:3000 