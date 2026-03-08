import { PrismaClient } from '@prisma/client';
import path from 'path';

// Resolve database path relative to project root (one level up from server/)
const dbPath = path.resolve(__dirname, '..', '..', '..', 'prisma', 'dev.db');

const prisma = new PrismaClient({
  datasources: {
    db: {
      url: `file:${dbPath}`,
    },
  },
});

export default prisma;
