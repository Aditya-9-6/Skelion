import os
import json

target_dir = os.path.join("skelion_website", "node_modules", "@alloc", "quick-lru")
target_pkg = os.path.join(target_dir, "package.json")
target_js = os.path.join(target_dir, "quick-lru.js")

with open(target_pkg, "r", encoding="utf-8") as f:
    pkg = json.load(f)

pkg["main"] = "quick-lru.js"

with open(target_pkg, "w", encoding="utf-8") as f:
    json.dump(pkg, f, indent=2)

js_content = """'use strict';

class QuickLRU {
  constructor(options = {}) {
    this.maxSize = options.maxSize || 1000;
    this.clear();
  }

  clear() {
    this.cache = new Map();
    this.oldCache = new Map();
    this._size = 0;
  }

  get size() {
    return this._size;
  }

  _set(key, value) {
    this.cache.set(key, value);
    this._size++;

    if (this._size >= this.maxSize) {
      this._size = 0;
      this.oldCache = this.cache;
      this.cache = new Map();
    }
  }

  get(key) {
    if (this.cache.has(key)) {
      return this.cache.get(key);
    }
    if (this.oldCache.has(key)) {
      const value = this.oldCache.get(key);
      this.oldCache.delete(key);
      this._set(key, value);
      return value;
    }
  }

  set(key, value) {
    if (this.cache.has(key)) {
      this.cache.set(key, value);
    } else {
      this._set(key, value);
    }
    return this;
  }

  has(key) {
    return this.cache.has(key) || this.oldCache.has(key);
  }

  peek(key) {
    if (this.cache.has(key)) return this.cache.get(key);
    if (this.oldCache.has(key)) return this.oldCache.get(key);
  }

  delete(key) {
    const deleted = this.cache.delete(key);
    if (deleted) this._size--;
    return this.oldCache.delete(key) || deleted;
  }

  *keys() {
    for (const [key] of this) {
      yield key;
    }
  }

  *values() {
    for (const [, value] of this) {
      yield value;
    }
  }

  *[Symbol.iterator]() {
    for (const item of this.cache) {
      yield item;
    }
    for (const item of this.oldCache) {
      if (!this.cache.has(item[0])) {
        yield item;
      }
    }
  }

  *entriesAscending() {
    for (const item of this) {
      yield item;
    }
  }

  *entriesDescending() {
    const items = [...this];
    for (let i = items.length - 1; i >= 0; i--) {
      yield items[i];
    }
  }
}

module.exports = QuickLRU;
"""

with open(target_js, "w", encoding="utf-8") as f:
    f.write(js_content)

print("SUCCESS: Configured @alloc/quick-lru with quick-lru.js as main entrypoint")
