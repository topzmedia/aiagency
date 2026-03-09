-- RedefineTables
PRAGMA defer_foreign_keys=ON;
PRAGMA foreign_keys=OFF;
CREATE TABLE "new_GeneratedOutput" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "projectId" TEXT,
    "verticalId" TEXT NOT NULL,
    "outputType" TEXT NOT NULL,
    "hookBlockId" TEXT,
    "problemBlockId" TEXT,
    "discoveryBlockId" TEXT,
    "benefitBlockId" TEXT,
    "ctaBlockId" TEXT,
    "fullText" TEXT NOT NULL,
    "combinationHash" TEXT NOT NULL,
    "status" TEXT NOT NULL DEFAULT 'DRAFT',
    "notes" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    CONSTRAINT "GeneratedOutput_projectId_fkey" FOREIGN KEY ("projectId") REFERENCES "Project" ("id") ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT "GeneratedOutput_verticalId_fkey" FOREIGN KEY ("verticalId") REFERENCES "Vertical" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);
INSERT INTO "new_GeneratedOutput" ("benefitBlockId", "combinationHash", "createdAt", "ctaBlockId", "discoveryBlockId", "fullText", "hookBlockId", "id", "notes", "outputType", "problemBlockId", "projectId", "status", "updatedAt", "verticalId") SELECT "benefitBlockId", "combinationHash", "createdAt", "ctaBlockId", "discoveryBlockId", "fullText", "hookBlockId", "id", "notes", "outputType", "problemBlockId", "projectId", "status", "updatedAt", "verticalId" FROM "GeneratedOutput";
DROP TABLE "GeneratedOutput";
ALTER TABLE "new_GeneratedOutput" RENAME TO "GeneratedOutput";
CREATE UNIQUE INDEX "GeneratedOutput_combinationHash_key" ON "GeneratedOutput"("combinationHash");
PRAGMA foreign_keys=ON;
PRAGMA defer_foreign_keys=OFF;
