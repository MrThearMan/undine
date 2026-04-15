// If the url has a hash, and a details element with that id exists, open it on page load.
document.addEventListener("DOMContentLoaded", () => {
  if (!window.location.hash) return;

  const elem = document.querySelector(window.location.hash)
  if (!elem) return;

  if (elem.tagName === "DETAILS") {
    elem.open = true
  }
});

// When a details element is opened, make its id the URL hash, if it has one.
// When the element is closed, remove the hash from the URL.
document.querySelectorAll("details").forEach(details => {
  details.addEventListener("toggle", () => {
    if (details.open && details.id) {
      history.replaceState(null, "", `#${details.id}`);
    }
    else if (!details.open && `#${details.id}` === window.location.hash) {
      history.replaceState(null, "", window.location.pathname);
    }
  });
});


// When an anchor containing a hash is clicked, and the hash corresponds to an
// id of a details element, open the details element.
document.addEventListener("click", event => {
  const anchor = event.target.closest('a[href^="#"]');
  if (!anchor) return;

  const href = anchor.getAttribute("href");
  if (!href) return;

  const elem = document.querySelector(href);
  if (!elem) return;

  if (elem.tagName === "DETAILS") {
    elem.open = true;
  }
});


// Register the service worker for caching docs offline
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/undine/service-worker.js', { scope: '/undine/' })
      .then(reg => console.log('Service Worker registered:', reg.scope))
      .catch(err => console.error('Service Worker registration failed:', err));
  });
}
