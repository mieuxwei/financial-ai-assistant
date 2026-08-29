var DEMO_STATE_TTL_SECONDS_ = 900;
var DEMO_USER_COMMANDS_PER_MINUTE_ = 30;
var DEMO_GLOBAL_COMMANDS_PER_MINUTE_ = 300;

function enforceDemoRateLimit_(principalId) {
  var lock = LockService.getScriptLock();
  if (!lock.tryLock(1000)) throw new Error("rate limit unavailable");
  try {
    var cache = CacheService.getScriptCache();
    var minute = Math.floor(Date.now() / 60000);
    var userKey = "demo_rate:user:" + principalId + ":" + minute;
    var globalKey = "demo_rate:global:" + minute;
    var userCount = Number(cache.get(userKey) || "0");
    var globalCount = Number(cache.get(globalKey) || "0");
    if (userCount >= DEMO_USER_COMMANDS_PER_MINUTE_ ||
        globalCount >= DEMO_GLOBAL_COMMANDS_PER_MINUTE_) {
      throw new Error("demo command rate exceeded");
    }
    cache.put(userKey, String(userCount + 1), 120);
    cache.put(globalKey, String(globalCount + 1), 120);
  } finally {
    lock.releaseLock();
  }
}

function getDemoState_(principalId) {
  var value = CacheService.getScriptCache().get(stateKey_(principalId));
  return value ? JSON.parse(value) : null;
}

function setDemoState_(principalId, state) {
  CacheService.getScriptCache().put(
    stateKey_(principalId),
    JSON.stringify(state),
    DEMO_STATE_TTL_SECONDS_
  );
}

function clearDemoState_(principalId) {
  CacheService.getScriptCache().remove(stateKey_(principalId));
}

function stateKey_(principalId) {
  return "demo_state:" + principalId;
}
