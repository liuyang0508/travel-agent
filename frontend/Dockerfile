FROM node:20-alpine

WORKDIR /app

RUN npm config set registry https://registry.npmmirror.com

COPY package.json .
RUN npm install

COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev"]
