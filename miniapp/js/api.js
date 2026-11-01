/** Shared Macro Alert API client. Uses Telegram.WebApp.initData only. */
(function (global) {
  var API_BASE = (global.MACRO_API_BASE || '').replace(/\/$/, '');

  function getInitData() {
    try {
      if (global.Telegram && global.Telegram.WebApp && global.Telegram.WebApp.initData) {
        return global.Telegram.WebApp.initData;
      }
    } catch (e) {}
    return '';
  }

  function apiAvailable() {
    return !!API_BASE;
  }

  async function apiFetch(path, options) {
    if (!API_BASE) {
      var err = new Error('API not configured');
      err.code = 'NO_API';
      throw err;
    }
    var initData = getInitData();
    if (!initData) {
      var e2 = new Error('Missing Telegram initData');
      e2.code = 'NO_INITDATA';
      throw e2;
    }
    options = options || {};
    var headers = Object.assign({
      'Content-Type': 'application/json',
      'X-Telegram-Init-Data': initData
    }, options.headers || {});
    var res = await fetch(API_BASE + path, {
      method: options.method || 'GET',
      headers: headers,
      body: options.body ? JSON.stringify(options.body) : undefined,
      cache: 'no-store'
    });
    if (res.status === 401 || res.status === 403) {
      var a = new Error('Unauthorized');
      a.code = 'AUTH';
      a.status = res.status;
      throw a;
    }
    if (res.status === 429) {
      var r = new Error('Rate limited');
      r.code = 'RATE';
      throw r;
    }
    if (!res.ok) {
      var s = new Error('Server error ' + res.status);
      s.code = 'SERVER';
      s.status = res.status;
      throw s;
    }
    return res.json();
  }

  global.MacroAPI = {
    available: apiAvailable,
    getMe: function () { return apiFetch('/api/me'); },
    getSettings: function () { return apiFetch('/api/me/settings'); },
    patchSettings: function (body) { return apiFetch('/api/me/settings', { method: 'PATCH', body: body }); },
    getNews: function (params) {
      var q = new URLSearchParams(params || {}).toString();
      return apiFetch('/api/news' + (q ? '?' + q : ''));
    },
    getNewsOne: function (id) { return apiFetch('/api/news/' + encodeURIComponent(id)); },
    getCategories: function () { return apiFetch('/api/news/categories'); },
    getCalendar: function () { return apiFetch('/api/calendar'); },
    getMarketStatus: function () { return apiFetch('/api/market/status'); }
  };
})(window);
