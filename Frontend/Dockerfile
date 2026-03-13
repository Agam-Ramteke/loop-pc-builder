FROM node:20-slim

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm install

# Port to expose
EXPOSE 3000

# Recommended command for Next.js development
CMD ["npm", "run", "dev"]
