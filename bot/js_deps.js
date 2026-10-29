// Every Node package the Python side uses, loaded from here so they resolve from
// bot/node_modules (i.e. bot/package.json). A bare require("mineflayer") from Python
// resolves from JSPyBridge's own private install dir inside the venv instead, which ignores
// package.json and keeps whatever version it auto-installed first.
module.exports = {
  mineflayer: require('mineflayer'),
  skyhelper: require('skyhelper-networth'),
  applyMcPatches: require('./mc_patches')
}
