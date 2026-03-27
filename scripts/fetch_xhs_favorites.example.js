#!/usr/bin/env node
/**
 * Directly call rednote-mcp's getFavorites to fetch XHS favorites.
 * Outputs JSON array of notes to stdout.
 *
 * Prerequisites:
 *   npm install -g rednote-mcp
 *   rednote-mcp init  (to login)
 *
 * Usage: node fetch_xhs_favorites.js [limit]
 *
 * Copy this file to fetch_xhs_favorites.js and update the path below.
 */
const path = require('path');

// Update this path to match your rednote-mcp installation
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
    console.log(JSON.stringify(notes, null, 2));
  } catch (err) {
    console.error('Error:', err.message);
    process.exit(1);
  }
})();
