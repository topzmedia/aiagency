import { PrismaClient } from '@prisma/client';
import path from 'path';

// Use process.cwd() since server runs from project root
const dbPath = path.join(process.cwd(), 'prisma', 'dev.db');

const prisma = new PrismaClient({
  datasources: {
    db: {
      url: `file:${dbPath}`,
    },
  },
});

export default prisma;
