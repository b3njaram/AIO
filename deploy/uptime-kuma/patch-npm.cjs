// Apply only reviewed, hash-pinned package upgrades to the existing runtime tree.
// Never run dependency lifecycle scripts or reinstall native application modules.
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { execFileSync } = require('node:child_process');
const { createRequire } = require('node:module');
const semver = require('/usr/local/lib/node_modules/npm/node_modules/semver');
const plan = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
function check(ok, message) { if (!ok) throw new Error(message); }
function readManifest(dir) { return JSON.parse(fs.readFileSync(path.join(dir, 'package.json'), 'utf8')); }
function findDependency(dir, name) {
  // Node's package lookup walks enclosing node_modules, regardless of exports.
  for (let current = dir; ; current = path.dirname(current)) {
    const candidate = path.join(current, 'node_modules', name, 'package.json');
    if (fs.existsSync(candidate)) return JSON.parse(fs.readFileSync(candidate, 'utf8'));
    if (current === path.dirname(current)) return null;
  }
}
for (const row of plan.packages) {
  const dir = row.path;
  check(dir.startsWith('/app/node_modules/') || dir.startsWith('/usr/local/lib/node_modules/npm/node_modules/'), 'Unapproved patch path');
  check(path.normalize(dir) === dir && dir.endsWith('/' + row.name), 'Unexpected package path');
  check(fs.realpathSync(dir) === dir && fs.lstatSync(dir).isDirectory(), 'Unexpected package directory');
  const old = readManifest(dir), stat = fs.statSync(dir);
  check(old.name === row.name && old.version === row.from, 'Unexpected installed package ' + row.name);
  check(semver.major(row.to) === semver.major(row.from) && semver.gt(row.to, row.from), 'Only same-major upgrades allowed');
  check(/^https:\/\/registry\.npmjs\.org\//.test(row.url) && /^sha512-[A-Za-z0-9+/]+=*$/.test(row.integrity), 'Unapproved artifact');
  check(/^[a-f0-9]{64}$/.test(row.sha256), 'Invalid pinned archive digest');
  const archive = path.join('/archives', row.sha256 + '.tgz');
  const staging = fs.mkdtempSync(path.join(path.dirname(dir), '.jobbi-patch-'));
  try {
    const integrity = 'sha512-' + crypto.createHash('sha512').update(fs.readFileSync(archive)).digest('base64');
    check(integrity === row.integrity, 'Package integrity mismatch: ' + row.name);
    execFileSync('tar', ['-xzf', archive, '--strip-components=1', '--no-same-owner', '--no-same-permissions', '-C', staging], { stdio: 'inherit' });
    const next = readManifest(staging);
    check(next.name === row.name && next.version === row.to, 'Archive identity mismatch');
    if (next.engines?.node) check(semver.satisfies(process.version, next.engines.node), 'Unsupported Node runtime');
    // OverlayFS can reject renaming a directory from the upstream layer.
    // Keep the directory and any existing nested dependencies in place.
    check(!fs.existsSync(path.join(staging, 'node_modules')), 'Unexpected bundled dependencies');
    for (const entry of fs.readdirSync(dir)) {
      if (entry !== 'node_modules') fs.rmSync(path.join(dir, entry), { recursive: true });
    }
    for (const entry of fs.readdirSync(staging)) {
      const target = path.join(dir, entry);
      fs.renameSync(path.join(staging, entry), target);
      execFileSync('chown', ['-hR', stat.uid + ':' + stat.gid, target]);
    }
    for (const [name, range] of Object.entries(next.dependencies || {})) {
      const dep = findDependency(dir, name);
      check(dep && semver.satisfies(dep.version, range), 'Missing compatible dependency ' + row.name + ' -> ' + name);
    }
    check(readManifest(dir).version === row.to, 'Patched version mismatch');
    // Load the actual installed entry point, without executing installation scripts.
    const local = createRequire(path.join(path.dirname(dir), '__jobbi_check__.cjs'));
    const resolved = local.resolve(row.name);
    check(resolved.startsWith(dir + '/'), 'Runtime resolved a different package: ' + row.name);
    local(row.name);
    console.log('Verified npm security update:', row.name, row.from, '->', row.to);
  } finally {
    fs.rmSync(staging, { recursive: true, force: true });
  }
}
