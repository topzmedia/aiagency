// LF8-Driven Content Bank
// 8 verticals × 5 block types × 100 entries = 4,000 unique copy lines
// LF8 (Life Force 8) drives: survival, food, freedom from fear/danger, sexual companionship,
// comfortable living, superiority, care for loved ones, social approval
// 70% first-person storytelling | Cashvertising & Gary Halbert principles

import {
  autoInsurance,
  homeInsurance,
  roofing,
  homeWindows,
  homeWarranty,
  heloc,
  mortgageRefinance,
  debtRelief,
} from './verticals';

export const contentBank: Record<string, Record<string, string[]>> = {
  'Auto Insurance': autoInsurance,
  'Home Insurance': homeInsurance,
  'Roofing': roofing,
  'Home Windows Replacement': homeWindows,
  'Home Warranty': homeWarranty,
  'HELOC': heloc,
  'Mortgage Refinance': mortgageRefinance,
  'Debt Relief': debtRelief,
};
