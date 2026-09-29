// Plan 06 AC7-d: cross-language check helper (called by tests/test_frontend_contract.py).
// Usage: node frontend/tests/build_body_cli.mjs <in.json> <out.json>
//   in.json  = {"hand_frames": [...], "segment_id": int, "max_frames": int, "top_k": int}
//   out.json = buildSequenceBody(...) of frontend/src/lib/fingerspelling.js
import { readFileSync, writeFileSync } from 'node:fs';

import { buildSequenceBody } from '../src/lib/fingerspelling.js';

const [, , inPath, outPath] = process.argv;
if (!inPath || !outPath) {
  console.error('usage: node build_body_cli.mjs <in.json> <out.json>');
  process.exit(2);
}
const input = JSON.parse(readFileSync(inPath, 'utf8'));
const body = buildSequenceBody(input.hand_frames, {
  segmentId: input.segment_id, maxFrames: input.max_frames, topK: input.top_k,
});
writeFileSync(outPath, JSON.stringify(body));
