# Apenas Promo - Web Layer

This is the web storefront for Apenas Promo, focused on Programmatic SEO to attract organic traffic from Google.

## Setup

1. Install dependencies:

   ```bash
   cd backend && npm install
   cd ../web && npm install
   ```

2. For the backend (SQLite - no database server needed):
   - The database is a local file `dev.db` in the backend folder.
   - Run migrations:
     ```bash
     cd backend
     npx prisma migrate dev --name init
     ```

3. Start the backend:

   ```bash
   cd backend
   npm run dev
   ```

   Server runs on http://localhost:3000

4. For the frontend (requires Node.js 20.12+):
   - Update Node.js if needed (current version 20.11.0 is too old).
   - Start development server:
     ```bash
     cd web
     npm run dev
     ```
     Nuxt runs on http://localhost:3000 (adjust port if backend is running).

## Architecture

- **Backend**: Node.js + Fastify + Prisma + SQLite (file-based, no server needed)
- **Frontend**: Nuxt 3 + Vue 3 + TailwindCSS

The system is designed for high performance and SEO optimization for Google indexing.
