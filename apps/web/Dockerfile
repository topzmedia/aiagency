FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN if [ -f package.json ]; then npm install; else echo '{"name":"content-finder-web","version":"0.1.0","private":true,"scripts":{"dev":"next dev","build":"next build","start":"next start"},"dependencies":{"next":"14.1.0","react":"18.2.0","react-dom":"18.2.0"},"devDependencies":{"@types/node":"20.11.0","@types/react":"18.2.48","typescript":"5.3.3"}}' > package.json && npm install; fi

# Copy application code
COPY . .

# Build (skip if no pages exist yet)
RUN if [ -d "src" ] || [ -d "pages" ] || [ -d "app" ]; then npm run build 2>/dev/null || true; fi

EXPOSE 3000

ENV NEXT_PUBLIC_API_URL=http://localhost:8000

# Use dev mode for development
CMD ["npm", "run", "dev"]
