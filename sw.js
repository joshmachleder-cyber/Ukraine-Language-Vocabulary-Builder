// Cache version. Bump this whenever index.html changes.
var CACHE = "uk-vocab-v7";

var SHELL = [
  "./",
  "./index.html",
  "./manifest.webmanifest",
  "./words.json",
  "./examples.json"
];

self.addEventListener("install", function(e){
  e.waitUntil(
    caches.open(CACHE).then(function(c){ return c.addAll(SHELL); })
         .then(function(){ return self.skipWaiting(); })
  );
});

self.addEventListener("activate", function(e){
  e.waitUntil(
    caches.keys().then(function(keys){
      return Promise.all(keys.map(function(k){
        if (k !== CACHE) return caches.delete(k);
      }));
    }).then(function(){ return self.clients.claim(); })
  );
});

self.addEventListener("fetch", function(e){
  // The Google Sheet is left alone: the page reads it fresh every time and
  // keeps its own copy for offline use.
  if (e.request.url.indexOf(self.location.origin) !== 0) return;

  // App files: network first, so changes to the app show up right away,
  // with the cached copy as the offline fallback.
  e.respondWith(
    fetch(e.request).then(function(res){
      var copy = res.clone();
      caches.open(CACHE).then(function(c){ c.put(e.request, copy); });
      return res;
    }).catch(function(){
      return caches.match(e.request);
    })
  );
});
