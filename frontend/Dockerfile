# Portfolio Navigator Wizard - Frontend
# Multi-stage build: Node for building, nginx for serving

# Stage 1: Build the React app
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files first for better caching
COPY package*.json ./
RUN npm ci

# Copy source and build
COPY . .

# Set the API URL for production build
ARG VITE_API_BASE_URL=https://portfolio-navigator-wizard.fly.dev
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

# Stage 2: Serve with nginx
FROM nginx:alpine

# Copy custom nginx config for SPA routing
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built files from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose port 8080 (Fly.io default)
EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
