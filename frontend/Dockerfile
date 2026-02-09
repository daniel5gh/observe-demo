FROM node:20-alpine AS build
WORKDIR /app
ARG VITE_OTEL_AUTHORIZATION
ENV VITE_OTEL_AUTHORIZATION=$VITE_OTEL_AUTHORIZATION
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
