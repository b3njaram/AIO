// Apply only reviewed, hash-pinned package upgrades to the existing runtime tree.
// Never run dependency lifecycle scripts or reinstall native application modules.
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
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
const work = fs.mkdtempSync(path.join(os.tmpdir(), 'jobbi-npm-security-'));
try {
  for (const row of plan.packages) {
    const dir = row.path;
    check(dir.startsWith('/app/node_modules/') || dir.startsWith('/usr/local/lib/node_modules/npm/node_modules/'), 'Unapproved patch path');
    check(path.normalize(dir) === dir && dir.endsWith('/' + row.name), 'Unexpected package path');
    check(fs.realpathSync(dir) === dir && fs.lstatSync(dir).isDirectory(), 'Unexpected package directory');
    const old = readManifest(dir), stat = fs.statSync(dir);
    check(old.name === row.name && old.version === row.from, 'Unexpected installed package ' + row.name);
    check(semver.major(row.to) === semver.major(row.from) && semver.gt(row.to, row.from), 'Only same-major upgrades allowed');
    check(/^https:\/\/registry\.npmjs\.org\//.test(row.url) && /^sha512-[A-Za-z0-9+/]+=*$/.test(row.integrity), 'Unapproved artifact');
    const archive = path.join(work, 'package.tgz');
    const staging = fs.mkdtempSync(path.join(path.dirname(dir), '.jobbi-patch-'));
    try {
      execFileSync('curl', ['--fail', '--silent', '--show-error', '--location', '--proto', '=https', '--proto-redir', '=https', '--retry', '3', '--max-time', '120', row.url, '-o', archive], { stdio: 'inherit' });
      const integrity = 'sha512-' + crypto.createHash('sha512').update(fs.readFileSync(archive)).digest('base64');
      check(integrity === row.integrity, 'Package integrity mismatch: ' + row.name);
      execFileSync('tar', ['-xzf', archive, '--strip-components=1', '--no-same-owner', '--no-same-permissions', '-C', staging], { stdio: 'inherit' });
      const next = readManifest(staging);
      check(next.name === row.name && next.version === row.to, 'Archive identity mismatch');
      if (next.engines?.node) check(semver.satisfies(process.version, next.engines.node), 'Unsupported Node runtime');
      // Keep any nested dependencies; do not resolve new dependencies from the network.
      const nested = path.join(dir, 'node_modules');
      if (fs.existsSync(nested)) {
        check(!fs.existsSync(path.join(staging, 'node_modules')), 'Unexpected bundled dependencies');
        fs.renameSync(nested, path.join(staging, 'node_modules'));
      }
      const retired = path.join(path.dirname(dir), '.jobbi-retired-' + path.basename(staging));
      fs.renameSync(dir, retired);
      fs.renameSync(staging, dir);
      fs.chmodSync(dir, stat.mode & 0o777);
      execFileSync('chown', ['-hR', stat.uid + ':' + stat.gid, dir]);
      for (const [name, range] of Object.entries(next.dependencies || {})) {
        const dep = findDependency(dir, name);
        check(dep && semver.satisfies(dep.version, range), 'Missing compatible dependency ' + row.name + ' -> ' + name);
      }
      fs.rmSync(retired, { recursive: true, force: true });
      check(readManifest(dir).version === row.to, 'Patched version mismatch');
      // Load the actual installed entry point, without executing installation scripts.
      const local = createRequire(path.join(path.dirname(dir), '__jobbi_check__.cjs'));
      const resolved = local.resolve(row.name);
      check(resolved.startsWith(dir + '/'), 'Runtime resolved a different package: ' + row.name);
      local(row.name);
      console.log('Verified npm security update:', row.name, row.from, '->', row.to);
    } finally {
      fs.rmSync(archive, { force: true });
      fs.rmSync(staging, { recursive: true, force: true });
    }
  }
} finally {
  fs.rmSync(work, { recursive: true, force: true });
}
