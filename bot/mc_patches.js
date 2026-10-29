// Runtime fixes applied to every Mineflayer bot right after createBot() (see main.py). Both
// only matter on 1.20.2+ (where Hypixel re-enters the configuration phase on every server
// switch) and are inert on 1.8.9. Mineflayer's movement packets are fixed separately, in
// patches/mineflayer+<version>.patch (applied by patch-package on npm install).

// Mineflayer's resource pack plugin answers with a uuid-1345 object instead of a UUID
// string, which minecraft-protocol serializes as all zeros. Hypixel's SkyBlock servers
// force a resource pack during configuration and never finish it without a reply for the
// real pack id, so the bot hangs mid-switch forever. Send the string form instead.
function fixResourcePackUuid (bot) {
  const write = bot._client.write.bind(bot._client)
  bot._client.write = (name, params) => {
    if (name === 'resource_pack_receive' && params && params.uuid && typeof params.uuid === 'object') {
      params = { ...params, uuid: params.uuid.toString() }
    }
    return write(name, params)
  }
}

// A chat packet sent while the connection is in the configuration phase (mid server switch)
// makes Hypixel close the socket. Hold anything sent then and flush it once back in play.
function queueChatDuringConfiguration (bot) {
  const queue = []
  let chat
  // bot.chat comes from a plugin Mineflayer loads on 'inject_allowed', just after
  // createBot() returns; its own listener is registered first, so ours runs after it.
  bot.once('inject_allowed', () => {
    chat = bot.chat.bind(bot)
    bot.chat = (message) => {
      if (bot._client.state === 'play') return chat(message)
      queue.push(message)
    }
  })
  bot._client.on('state', (state) => {
    if (state !== 'play' || queue.length === 0) return
    // Give the respawn that follows a switch a moment to land, then send one message every
    // half second so a backlog doesn't trip Hypixel's command spam limit.
    const flush = () => {
      if (queue.length === 0 || bot._client.state !== 'play') return
      chat(queue.shift())
      setTimeout(flush, 500)
    }
    setTimeout(flush, 1000)
  })
}

module.exports = function applyPatches (bot) {
  fixResourcePackUuid(bot)
  queueChatDuringConfiguration(bot)
}
