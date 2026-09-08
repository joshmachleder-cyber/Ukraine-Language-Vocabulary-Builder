// Cache version. Bump this whenever index.html changes, or phones with the
// app on the home screen will keep running the old copy.
var CACHE = "uk-vocab-v3";

var SHELL = [
  "./",
  "./index.html",
  "./manifest.webmanifest"
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

function isWordList(url){
  return url.indexOf("docs.google.com") >= 0
      || url.indexOf("googleusercontent.com") >= 0
      || url.indexOf("words.json") >= 0;
}

self.addEventListener("fetch", function(e){
  var url = e.request.url;

  // The word list is the one thing that changes daily. Always try the
  // network first and fall back to the cached copy, so an offline session
  // still works but a fresh one gets today's words.
  if (isWordList(url)){
    e.respondWith(
      fetch(e.request).then(function(res){
        var copy = res.clone();
        caches.open(CACHE).then(function(c){ c.put(e.request, copy); });
        return res;
      }).catch(function(){
        return caches.match(e.request);
      })
    );
    return;
  }

  // Everything else is the app shell: cache first.
  e.respondWith(
    caches.match(e.request).then(function(hit){
      return hit || fetch(e.request);
    })
  );
});
