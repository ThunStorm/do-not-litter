// No network in frontend checks; Node IPC pipes remain available to Vitest workers.
const fs = require('node:fs');
const net = require('node:net');
const dns = require('node:dns');
const dgram = require('node:dgram');
function deny() {
  if (process.env.ZHIJIAN_NETWORK_AUDIT) fs.appendFileSync(process.env.ZHIJIAN_NETWORK_AUDIT, 'BLOCKED_NODE_NETWORK\n');
  throw new Error('Offline gate forbids network');
}
net.Socket.prototype.connect = deny;
dns.lookup = deny;
dns.resolve = deny;
dgram.Socket.prototype.send = deny;
process.on('exit', () => {
  const p = process.env.ZHIJIAN_NETWORK_AUDIT;
  if (p && fs.existsSync(p) && fs.statSync(p).size) process.exitCode = 91;
});
