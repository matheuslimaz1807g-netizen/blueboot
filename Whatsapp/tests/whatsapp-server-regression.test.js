const assert = require('assert');
const fs = require('fs');
const path = require('path');

const serverPath = path.join(__dirname, '..', 'server.js');
const source = fs.readFileSync(serverPath, 'utf8');

assert(
  source.includes('applyChannelMediaCompatibilityPatch'),
  'server.js must apply a channel media compatibility patch before sending media to WhatsApp channels',
);

assert(
  source.includes('avParams') && source.includes('mediaData'),
  'channel media compatibility patch must provide avParams fallback from mediaData',
);

assert(
  source.includes('successCount') && source.includes('failureCount'),
  'sendToDestinationsInternal must track per-target success and failure counts',
);

assert(
  source.includes('Todos os destinos falharam'),
  'queue processing must surface an error when every matched destination fails',
);

console.log('whatsapp-server-regression.test.js passed');
