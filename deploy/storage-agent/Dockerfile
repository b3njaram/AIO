FROM node:22-alpine@sha256:1314fb30ec37592d5845e5a160d522c0e680972aa534549940b8d73bde88481a
RUN rm -rf /usr/local/lib/node_modules /opt/yarn* /root/.npm && rm -f /usr/local/bin/npm /usr/local/bin/npx /usr/local/bin/corepack /usr/local/bin/yarn /usr/local/bin/yarnpkg && node --version

# Check a recent successful snapshot, rather than only the process existing.
HEALTHCHECK --interval=60s --timeout=5s --start-period=120s --retries=3 CMD ["node","-e","const fs=require('node:fs');const s=JSON.parse(fs.readFileSync(process.env.STORAGE_OUTPUT||'/stats/storage.json'));const age=Date.now()-Date.parse(s.checkedAt);const ms=Math.max(300000,Number(process.env.STORAGE_INTERVAL_MS)||1800000);if(s.status!=='ready'||!Number.isFinite(age)||age<0||age>2*ms+60000)process.exit(1)"]
