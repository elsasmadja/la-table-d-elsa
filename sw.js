/* La Table d'Elsa — fonctionnement hors ligne
   Pour publier une mise à jour du site, incrémentez le numéro de version
   ci-dessous : les anciens fichiers mis en cache seront alors supprimés. */
const VERSION = 'elsa-v1';
const BASE = new URL('./', self.location).pathname;

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(VERSION)
      .then(c => c.addAll([BASE, BASE + 'index.html']))
      .catch(() => {})
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(noms => Promise.all(noms.filter(n => n !== VERSION).map(n => caches.delete(n))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;

  let url;
  try { url = new URL(req.url); } catch (err) { return; }

  // Tout ce qui est externe (Supabase, polices distantes) passe par le réseau.
  if (url.origin !== self.location.origin) return;

  // La page elle-même : on privilégie le réseau pour avoir la dernière version,
  // et on retombe sur le cache si la connexion manque.
  if (req.mode === 'navigate') {
    e.respondWith(
      fetch(req)
        .then(rep => {
          const copie = rep.clone();
          caches.open(VERSION).then(c => c.put(req, copie));
          return rep;
        })
        .catch(() => caches.match(req).then(r => r || caches.match(BASE + 'index.html')))
    );
    return;
  }

  // Images et autres fichiers : cache d'abord, réseau ensuite.
  e.respondWith(
    caches.match(req).then(hit => hit || fetch(req).then(rep => {
      if (rep && rep.ok && rep.type === 'basic') {
        const copie = rep.clone();
        caches.open(VERSION).then(c => c.put(req, copie));
      }
      return rep;
    }))
  );
});
