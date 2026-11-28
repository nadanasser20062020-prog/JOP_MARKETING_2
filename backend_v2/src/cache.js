export class MemoryCache {
  #entries = new Map();
  #ttlMs;
  #maxEntries;

  constructor({ ttlMs = 30_000, maxEntries = 100 } = {}) {
    this.#ttlMs = ttlMs;
    this.#maxEntries = maxEntries;
  }

  get(key) {
    const entry = this.#entries.get(key);
    if (!entry) return undefined;
    if (entry.expiresAt <= Date.now()) {
      this.#entries.delete(key);
      return undefined;
    }
    return entry.value;
  }

  set(key, value) {
    if (this.#entries.size >= this.#maxEntries) {
      const firstKey = this.#entries.keys().next().value;
      if (firstKey !== undefined) this.#entries.delete(firstKey);
    }
    this.#entries.set(key, { value, expiresAt: Date.now() + this.#ttlMs });
    return value;
  }

  getOrSet(key, factory) {
    const cached = this.get(key);
    if (cached !== undefined) return cached;
    return this.set(key, factory());
  }

  clear() {
    this.#entries.clear();
  }
}
