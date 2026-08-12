/* La Table d'Elsa — fonctionnement hors ligne
   Pour publier une mise à jour du site, incrémentez le numéro de version
   ci-dessous : les anciens fichiers mis en cache seront alors supprimés. */
const VERSION = 'elsa-v3';
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


/* ── Notifications : nouvelle recette ─────────────────────────────
   Le push arrive sans contenu. Le service worker va lire le fichier
   derniere-recette.json du site pour savoir quoi annoncer. */
self.addEventListener('push', e => {
  e.waitUntil((async () => {
    let titre = 'La Table d\u2019Elsa';
    let corps = 'Une nouvelle recette vient d\u2019arriver.';
    let cible = BASE;
    try {
      const rep = await fetch(BASE + 'derniere-recette.json?t=' + Date.now(), { cache: 'no-store' });
      if (rep.ok) {
        const info = await rep.json();
        if (info.titre) titre = info.titre;
        if (info.texte) corps = info.texte;
        if (info.onglet) cible = BASE + '#' + info.onglet;
      }
    } catch (err) {}
    await self.registration.showNotification(titre, {
      body: corps,
      icon: BASE + 'images/icon-192.png',
      badge: BASE + 'images/icon-192.png',
      tag: 'nouvelle-recette',
      renotify: true,
      data: { url: cible }
    });
  })());
});

self.addEventListener('notificationclick', e => {
  e.notification.close();
  const cible = (e.notification.data && e.notification.data.url) || BASE;
  e.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(liste => {
      for (const c of liste) {
        if (c.url.indexOf(cible) !== -1 && 'focus' in c) return c.focus();
      }
      return self.clients.openWindow(cible);
    })
  );
});
