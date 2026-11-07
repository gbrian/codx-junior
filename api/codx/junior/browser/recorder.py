"""In-page co-browsing recorder and compact page snapshot.

The browser is shared by a human (the live VNC view) and the AI (CDP tools).
Chromium cannot see the human's input through Playwright unless the page itself
reports it, so this module injects a tiny, dependency-free recorder:

* click / change / submit / Enter / scroll events are buffered **inside the
  page**, bounded to a few hundred entries;
* values from password / token / OTP fields are redacted before they leave the
  page;
* every event carries a stable CSS selector and a human-readable description;
* the AI can drain the buffer on its next action (or the runtime's watcher can
  drain it every second), which makes ``browser_activity`` truthful.

The same module contains :data:`SNAPSHOT_SCRIPT`, a compact accessibility-like
view of the page (interactive elements, refs, headings, main text).  It is much
cheaper for the model than 60 k characters of raw HTML and lets it click with
stable ``data-codx-ref`` attributes instead of brittle selectors.
"""

from __future__ import annotations

#: Version of the recorder payload.  Bump it when the JS contract changes.
RECORDER_VERSION = 1

#: Maximum events kept in the page before the oldest are dropped.
MAX_EVENTS = 300

#: Maximum characters returned for the main page text in a snapshot.
MAX_SNAPSHOT_TEXT = 6000

#: Maximum interactive elements returned in a snapshot.
MAX_SNAPSHOT_ELEMENTS = 250


RECORDER_SCRIPT = r"""
(() => {
  try {
    if (window.__codxRec && window.__codxRec.version === %(version)d) {
      window.__codxRec.install();
      return;
    }
    const MAX_EVENTS = %(max_events)d;
    const events = [];
    let actor = 'user';
    let lastActivity = Date.now();
    let scrollTimer = null;

    const esc = (value) => {
      const text = String(value == null ? '' : value);
      if (window.CSS && typeof window.CSS.escape === 'function') return window.CSS.escape(text);
      return text.replace(/["\\]/g, '\\$&');
    };
    const textOf = (el, limit) => {
      if (!el) return '';
      const value = (el.innerText || el.textContent || el.value || '').trim();
      return value.replace(/\s+/g, ' ').slice(0, limit || 120);
    };
    const isVisible = (el) => {
      if (!el || el.nodeType !== 1) return false;
      const rect = el.getBoundingClientRect ? el.getBoundingClientRect() : null;
      if (!rect || rect.width <= 0 || rect.height <= 0) return false;
      const style = window.getComputedStyle ? window.getComputedStyle(el) : null;
      if (!style) return true;
      return style.visibility !== 'hidden' && style.display !== 'none' && style.opacity !== '0';
    };
    const selectorOf = (el) => {
      if (!el || el.nodeType !== 1) return null;
      if (el === document.body) return 'body';
      if (el.id) return '#' + esc(el.id);
      const testId = el.getAttribute && (el.getAttribute('data-testid') || el.getAttribute('data-test-id') || el.getAttribute('data-qa'));
      if (testId) return '[data-testid="' + esc(testId) + '"]';
      const name = el.getAttribute && el.getAttribute('name');
      if (name) return el.tagName.toLowerCase() + '[name="' + esc(name) + '"]';
      const parts = [];
      let node = el;
      while (node && node.nodeType === 1 && node !== document.documentElement && parts.length < 6) {
        let part = node.tagName.toLowerCase();
        const parent = node.parentElement;
        if (parent) {
          const siblings = Array.from(parent.children).filter((child) => child.tagName === node.tagName);
          if (siblings.length > 1) part += ':nth-of-type(' + (siblings.indexOf(node) + 1) + ')';
        }
        parts.unshift(part);
        if (node.id) {
          parts.unshift('#' + esc(node.id));
          break;
        }
        node = parent;
      }
      return parts.join(' > ');
    };
    const isSensitive = (el) => {
      if (!el || !el.getAttribute) return false;
      const type = (el.getAttribute('type') || '').toLowerCase();
      if (type === 'password') return true;
      const hint = [
        el.getAttribute('name') || '',
        el.id || '',
        el.getAttribute('autocomplete') || '',
        el.getAttribute('aria-label') || '',
        el.getAttribute('placeholder') || ''
      ].join(' ').toLowerCase();
      return /pass|secret|token|otp|one[-_ ]?time|api[-_ ]?key|credit|card/.test(hint);
    };
    const describe = (el) => {
      if (!el || el.nodeType !== 1) return null;
      const type = (el.getAttribute && el.getAttribute('type') || '').toLowerCase();
      const sensitive = isSensitive(el);
      let value = null;
      let valueLength = null;
      if ('value' in el && typeof el.value === 'string') {
        valueLength = el.value.length;
        value = sensitive ? '***' : el.value.slice(0, 120);
      }
      return {
        tag: el.tagName ? el.tagName.toLowerCase() : null,
        id: el.id || null,
        name: (el.getAttribute && el.getAttribute('name')) || null,
        role: (el.getAttribute && el.getAttribute('role')) || null,
        type: type || null,
        text: textOf(el, 80),
        selector: selectorOf(el),
        value: value,
        value_length: valueLength,
        sensitive: sensitive,
        checked: typeof el.checked === 'boolean' ? el.checked : null,
        disabled: !!el.disabled
      };
    };
    const push = (kind, target, extra) => {
      if (actor !== 'user') return;
      try {
        events.push(Object.assign({
          kind: kind,
          ts: Date.now(),
          url: location.href,
          target: describe(target)
        }, extra || {}));
        if (events.length > MAX_EVENTS) events.splice(0, events.length - MAX_EVENTS);
        lastActivity = Date.now();
      } catch (e) { /* never break the page */ }
    };
    const onClick = (event) => push('click', event.target);
    const onChange = (event) => push('change', event.target);
    const onSubmit = (event) => push('submit', event.target);
    const onKeydown = (event) => {
      if (event.key === 'Enter') push('key', event.target, { key: 'Enter' });
    };
    const onScroll = () => {
      if (scrollTimer) return;
      scrollTimer = setTimeout(() => {
        scrollTimer = null;
        push('scroll', document.scrollingElement || document.documentElement, {
          x: Math.round(window.scrollX || 0),
          y: Math.round(window.scrollY || 0)
        });
      }, 400);
    };
    const install = () => {
      if (window.__codxRecInstalled) return;
      window.__codxRecInstalled = true;
      document.addEventListener('click', onClick, true);
      document.addEventListener('change', onChange, true);
      document.addEventListener('submit', onSubmit, true);
      document.addEventListener('keydown', onKeydown, true);
      window.addEventListener('scroll', onScroll, { passive: true });
    };

    window.__codxRec = {
      version: %(version)d,
      install: install,
      setActor: (value) => { actor = value === 'ai' ? 'ai' : 'user'; },
      drain: () => {
        try {
          install();
          const batch = events.splice(0, events.length);
          return {
            events: batch,
            url: location.href,
            title: document.title,
            active: describe(document.activeElement),
            selection: String(window.getSelection ? window.getSelection() : '').slice(0, 300),
            last_activity: lastActivity
          };
        } catch (e) {
          return { events: [], url: location.href, title: document.title };
        }
      },
      state: () => ({ events: events.length, actor: actor, last_activity: lastActivity })
    };
    install();
  } catch (e) { /* never break the page */ }
})();
""" % {"version": RECORDER_VERSION, "max_events": MAX_EVENTS}


SNAPSHOT_SCRIPT = r"""
(() => {
  try {
    const MAX_ELEMENTS = %(max_elements)d;
    const MAX_TEXT = %(max_text)d;
    const esc = (value) => {
      const text = String(value == null ? '' : value);
      if (window.CSS && typeof window.CSS.escape === 'function') return window.CSS.escape(text);
      return text.replace(/["\\]/g, '\\$&');
    };
    const textOf = (el, limit) => {
      if (!el) return '';
      const value = (el.innerText || el.textContent || el.value || '').trim();
      return value.replace(/\s+/g, ' ').slice(0, limit || 120);
    };
    const isVisible = (el) => {
      if (!el || el.nodeType !== 1) return false;
      const rect = el.getBoundingClientRect ? el.getBoundingClientRect() : null;
      if (!rect || rect.width <= 0 || rect.height <= 0) return false;
      const style = window.getComputedStyle ? window.getComputedStyle(el) : null;
      if (!style) return true;
      return style.visibility !== 'hidden' && style.display !== 'none' && style.opacity !== '0';
    };
    const selectorOf = (el) => {
      if (!el || el.nodeType !== 1) return null;
      if (el.id) return '#' + esc(el.id);
      const testId = el.getAttribute && (el.getAttribute('data-testid') || el.getAttribute('data-test-id') || el.getAttribute('data-qa'));
      if (testId) return '[data-testid="' + esc(testId) + '"]';
      const name = el.getAttribute && el.getAttribute('name');
      if (name) return el.tagName.toLowerCase() + '[name="' + esc(name) + '"]';
      const parts = [];
      let node = el;
      while (node && node.nodeType === 1 && node !== document.documentElement && parts.length < 6) {
        let part = node.tagName.toLowerCase();
        const parent = node.parentElement;
        if (parent) {
          const siblings = Array.from(parent.children).filter((child) => child.tagName === node.tagName);
          if (siblings.length > 1) part += ':nth-of-type(' + (siblings.indexOf(node) + 1) + ')';
        }
        parts.unshift(part);
        if (node.id) {
          parts.unshift('#' + esc(node.id));
          break;
        }
        node = parent;
      }
      return parts.join(' > ');
    };
    const isSensitive = (el) => {
      if (!el || !el.getAttribute) return false;
      const type = (el.getAttribute('type') || '').toLowerCase();
      if (type === 'password') return true;
      const hint = [
        el.getAttribute('name') || '',
        el.id || '',
        el.getAttribute('autocomplete') || '',
        el.getAttribute('aria-label') || ''
      ].join(' ').toLowerCase();
      return /pass|secret|token|otp|one[-_ ]?time|api[-_ ]?key|credit|card/.test(hint);
    };
    const describe = (el, index, withRef) => {
      const ref = withRef === false ? null : ('e' + index);
      if (ref) { try { el.setAttribute('data-codx-ref', ref); } catch (e) {} }
      const type = (el.getAttribute && el.getAttribute('type') || '').toLowerCase();
      const sensitive = isSensitive(el);
      let value = null;
      if ('value' in el && typeof el.value === 'string') {
        value = sensitive ? '***' : el.value.slice(0, 120);
      }
      return {
        ref: ref,
        tag: el.tagName ? el.tagName.toLowerCase() : null,
        role: (el.getAttribute && el.getAttribute('role')) || null,
        type: type || null,
        name: (el.getAttribute && (el.getAttribute('aria-label') || el.getAttribute('name') || el.getAttribute('placeholder'))) || textOf(el, 80),
        text: textOf(el, 80),
        selector: selectorOf(el),
        value: value,
        value_length: ('value' in el && typeof el.value === 'string') ? el.value.length : null,
        sensitive: sensitive,
        checked: typeof el.checked === 'boolean' ? el.checked : null,
        disabled: !!el.disabled,
        href: el.href || null
      };
    };

    const query = 'a[href],button,input,select,textarea,summary,[role="button"],[role="link"],[role="checkbox"],[role="radio"],[role="tab"],[role="menuitem"],[contenteditable="true"]';
    const elements = Array.from(document.querySelectorAll(query)).filter(isVisible).slice(0, MAX_ELEMENTS);
    const interactive = elements.map((el, index) => describe(el, index));

    const root = document.querySelector('main,article,[role="main"]') || document.body;
    const rawText = (root && (root.innerText || root.textContent)) || '';
    const text = rawText.replace(/\n{3,}/g, '\n\n').trim().slice(0, MAX_TEXT);
    const headings = Array.from(document.querySelectorAll('h1,h2,h3')).filter(isVisible).slice(0, 20).map((el) => ({
      level: Number(el.tagName.slice(1)),
      text: textOf(el, 120)
    }));
    const forms = Array.from(document.querySelectorAll('form')).filter(isVisible).slice(0, 20).map((form, index) => ({
      index: index,
      name: form.getAttribute('name') || form.id || null,
      action: form.getAttribute('action') || null,
      method: (form.getAttribute('method') || 'get').toLowerCase(),
      fields: Array.from(form.querySelectorAll('input,select,textarea')).filter(isVisible).slice(0, 40).map((el) => describe(el, -1, false))
    }));
    return {
      url: location.href,
      title: document.title,
      text: text,
      selection: String(window.getSelection ? window.getSelection() : '').slice(0, 800),
      active: describe(document.activeElement, -1, false),
      headings: headings,
      interactive: interactive,
      forms: forms,
      counts: {
        interactive: interactive.length,
        links: document.querySelectorAll('a[href]').length,
        images: document.querySelectorAll('img').length
      }
    };
  } catch (e) {
    return { error: String(e && e.message ? e.message : e), url: location.href, title: document.title };
  }
})();
""" % {"max_elements": MAX_SNAPSHOT_ELEMENTS, "max_text": MAX_SNAPSHOT_TEXT}
