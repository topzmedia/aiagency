import { Router } from 'express';
import { getVerticals } from '../controllers/verticalController';
import {
  getProjects,
  getProject,
  createProject,
  updateProject,
  deleteProject,
} from '../controllers/projectController';
import {
  getBlocks,
  getBlock,
  createBlock,
  updateBlock,
  deleteBlock,
  generateBlocksHandler,
  bulkApprove,
  bulkDelete,
} from '../controllers/blockController';
import {
  getOutputs,
  getOutput,
  composeOutputHandler,
  bulkGenerateHandler,
  updateOutput,
  deleteOutput,
} from '../controllers/outputController';
import {
  exportBlocksCSV,
  exportOutputsCSV,
  exportOutputsJSON,
} from '../controllers/exportController';
import { getTemplates } from '../services/templateService';

const router = Router();

// Verticals
router.get('/verticals', getVerticals);

// Projects
router.get('/projects', getProjects);
router.get('/projects/:id', getProject);
router.post('/projects', createProject);
router.put('/projects/:id', updateProject);
router.delete('/projects/:id', deleteProject);

// Blocks
router.get('/blocks', getBlocks);
router.get('/blocks/:id', getBlock);
router.post('/blocks', createBlock);
router.put('/blocks/:id', updateBlock);
router.delete('/blocks/:id', deleteBlock);
router.post('/blocks/generate', generateBlocksHandler);
router.post('/blocks/bulk-approve', bulkApprove);
router.post('/blocks/bulk-delete', bulkDelete);

// Outputs
router.get('/outputs', getOutputs);
router.get('/outputs/:id', getOutput);
router.post('/outputs/compose', composeOutputHandler);
router.post('/outputs/bulk-generate', bulkGenerateHandler);
router.put('/outputs/:id', updateOutput);
router.delete('/outputs/:id', deleteOutput);

// Export
router.get('/export/blocks.csv', exportBlocksCSV);
router.get('/export/outputs.csv', exportOutputsCSV);
router.get('/export/outputs.json', exportOutputsJSON);

// Templates
router.get('/templates', (_req, res) => {
  res.json(getTemplates());
});

export default router;
