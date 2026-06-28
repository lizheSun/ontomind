FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy application code
COPY . .

# Run Vite dev server
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
