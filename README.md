# Ad Variant Composer

A full-stack tool for generating, storing, composing, and exporting modular ad copy and video script variations for paid social campaigns.

## Tech Stack

- **Frontend**: React, Vite, TypeScript, Tailwind CSS, TanStack Query, React Router
- **Backend**: Node.js, Express, TypeScript, Prisma ORM, SQLite, Zod
- **Database**: SQLite (via Prisma)

## Setup

### 1. Install dependencies

```bash
npm install
cd client && npm install && cd ..
cd server && npm install && cd ..
```

### 2. Environment

```bash
cp .env.example .env
```

The default `.env` should work out of the box for local development.

### 3. Database setup

```bash
# Generate Prisma client
npm run prisma:generate

# Run migrations
npm run prisma:migrate

# Seed with demo data
npm run prisma:seed
```

### 4. Run the app

```bash
npm run dev
```

This starts both the backend (port 3001) and frontend (port 5173) concurrently.

- Frontend: http://localhost:5173
- Backend API: http://localhost:3001/api

## Features

- **Dashboard** — Summary cards, outputs by vertical, recent outputs
- **Projects** — Create, edit, delete projects with assigned verticals
- **Block Generator** — Generate ad copy blocks (hooks, problems, discoveries, benefits, CTAs) by vertical with configurable tone, audience, and count
- **Block Library** — Browse, filter, search, inline edit, bulk approve/delete blocks in card or table view
- **Composer** — Manually compose outputs from selected blocks with live preview, word/char count, and speaking time estimate
- **Bulk Generator** — Generate many unique combinations with optional block locking and duplicate prevention
- **Outputs Library** — View, filter, approve, archive, copy, and manage all generated outputs
- **Export** — Download blocks and outputs as CSV or JSON

## Seeded Verticals

- Home Insurance
- Auto Insurance
- Roofing
- Home Windows Replacement
- Home Warranty
- HELOC
- Mortgage Refinance
- Debt Relief

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/verticals | List all verticals |
| GET/POST | /api/projects | List / create projects |
| GET/PUT/DELETE | /api/projects/:id | Get / update / delete project |
| GET/POST | /api/blocks | List / create blocks |
| GET/PUT/DELETE | /api/blocks/:id | Get / update / delete block |
| POST | /api/blocks/generate | Generate blocks |
| POST | /api/blocks/bulk-approve | Bulk approve blocks |
| POST | /api/blocks/bulk-delete | Bulk delete blocks |
| GET | /api/outputs | List outputs |
| GET/PUT/DELETE | /api/outputs/:id | Get / update / delete output |
| POST | /api/outputs/compose | Compose single output |
| POST | /api/outputs/bulk-generate | Bulk generate outputs |
| GET | /api/templates | List composition templates |
| GET | /api/export/blocks.csv | Export blocks as CSV |
| GET | /api/export/outputs.csv | Export outputs as CSV |
| GET | /api/export/outputs.json | Export outputs as JSON |
