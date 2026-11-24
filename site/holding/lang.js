(function () {
  var KEY = 'km_lang';
  var pageLang = document.documentElement.lang; // 'mr' or 'en'
  var urls = { mr: '/', en: '/en/' };

  function read() {
    try { return localStorage.getItem(KEY); } catch (e) { return null; }
  }

  function save(lang) {
    try { localStorage.setItem(KEY, lang); } catch (e) {}
  }

  // Wire every [data-lang] element (popup options + header switch link)
  document.querySelectorAll('[data-lang]').forEach(function (el) {
    el.addEventListener('click', function () {
      save(el.getAttribute('data-lang'));
    });
  });

  var saved = read();

  if (saved && saved !== pageLang && urls[saved]) {
    // User has a saved preference different from this page's language → redirect
    location.replace(urls[saved]);
    return;
  }

  if (!saved) {
    // No preference saved yet → show popup if dialog is supported
    var dlg = document.getElementById('lang');
    if (dlg && typeof dlg.showModal === 'function') {
      dlg.showModal();
      // Esc closes the dialog natively; no choice is saved (correct behaviour)
    }
  }
  // If saved === pageLang: do nothing, user is on the right page
})();

