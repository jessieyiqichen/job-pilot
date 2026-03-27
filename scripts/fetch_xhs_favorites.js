#!/usr/bin/env node
/**
 * Directly call rednote-mcp's getFavorites to fetch XHS favorites.
 * Outputs JSON array of notes to stdout.
 * Usage: node fetch_xhs_favorites.js [limit]
 */
const path = require('path');
const rednotePath = path.join(
  process.env.HOME,
  '.npm-global/lib/node_modules/rednote-mcp/dist/tools/rednoteTools.js'
);
const { RedNoteTools } = require(rednotePath);

const limit = parseInt(process.argv[2] || '20', 10);

(async () => {
  const tools = new RedNoteTools();
  try {
    const notes = await tools.getFavorites(limit);
    // Output clean JSON to stdout
    console.log(JSON.stringify(notes, null, 2));
  } catch (err) {
    console.error('Error:', err.message);
    process.exit(1);
  }
})();
