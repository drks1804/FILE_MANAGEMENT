
# Stage 1: Build the Angular application
FROM node:22-alpine AS build

WORKDIR /app

# Copy package files first to improve build caching
COPY package*.json ./

RUN npm ci

# Copy Angular source code
COPY . .

# Build the application for production
RUN npm run build -- --configuration production
RUN mkdir /out && cp -r dist/*/browser/. /out/

# Stage 2: Serve the build using Nginx
FROM nginx:alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf

# Remove the default Nginx website
RUN rm -rf /usr/share/nginx/html/*

# Copy the Angular production build
COPY --from=build /out /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
