/**
 * Shared highlight.js instance built on the CORE bundle.
 *
 * `import hljs from 'highlight.js'` bundles ALL ~190 language definitions.
 * Because `Markdown.vue` was imported eagerly by `main.ts` (global component)
 * that payload ended up in the ENTRY chunk and blocked the first paint — the
 * "module evaluation" long task measured in production.
 *
 * Only the languages reachable from `EXTENSION_LANGUAGE_MAP`
 * (src/store/index.js) are registered here. Add a language below whenever a new
 * extension is supported.
 */
import hljs from 'highlight.js/lib/core'

import bash from 'highlight.js/lib/languages/bash'
import c from 'highlight.js/lib/languages/c'
import clojure from 'highlight.js/lib/languages/clojure'
import cpp from 'highlight.js/lib/languages/cpp'
import csharp from 'highlight.js/lib/languages/csharp'
import css from 'highlight.js/lib/languages/css'
import dart from 'highlight.js/lib/languages/dart'
import diff from 'highlight.js/lib/languages/diff'
import dockerfile from 'highlight.js/lib/languages/dockerfile'
import elixir from 'highlight.js/lib/languages/elixir'
import erlang from 'highlight.js/lib/languages/erlang'
import fsharp from 'highlight.js/lib/languages/fsharp'
import go from 'highlight.js/lib/languages/go'
import graphql from 'highlight.js/lib/languages/graphql'
import groovy from 'highlight.js/lib/languages/groovy'
import ini from 'highlight.js/lib/languages/ini'
import java from 'highlight.js/lib/languages/java'
import javascript from 'highlight.js/lib/languages/javascript'
import json from 'highlight.js/lib/languages/json'
import kotlin from 'highlight.js/lib/languages/kotlin'
import less from 'highlight.js/lib/languages/less'
import lua from 'highlight.js/lib/languages/lua'
import makefile from 'highlight.js/lib/languages/makefile'
import markdown from 'highlight.js/lib/languages/markdown'
import perl from 'highlight.js/lib/languages/perl'
import php from 'highlight.js/lib/languages/php'
import plaintext from 'highlight.js/lib/languages/plaintext'
import powershell from 'highlight.js/lib/languages/powershell'
import protobuf from 'highlight.js/lib/languages/protobuf'
import python from 'highlight.js/lib/languages/python'
import r from 'highlight.js/lib/languages/r'
import ruby from 'highlight.js/lib/languages/ruby'
import rust from 'highlight.js/lib/languages/rust'
import scala from 'highlight.js/lib/languages/scala'
import scss from 'highlight.js/lib/languages/scss'
import shell from 'highlight.js/lib/languages/shell'
import sql from 'highlight.js/lib/languages/sql'
import swift from 'highlight.js/lib/languages/swift'
import typescript from 'highlight.js/lib/languages/typescript'
import vbnet from 'highlight.js/lib/languages/vbnet'
import x86asm from 'highlight.js/lib/languages/x86asm'
import xml from 'highlight.js/lib/languages/xml'
import yaml from 'highlight.js/lib/languages/yaml'

const LANGUAGES = {
  bash,
  c,
  clojure,
  cpp,
  csharp,
  css,
  dart,
  diff,
  dockerfile,
  elixir,
  erlang,
  fsharp,
  go,
  graphql,
  groovy,
  ini,
  java,
  javascript,
  json,
  kotlin,
  less,
  lua,
  makefile,
  markdown,
  perl,
  php,
  plaintext,
  powershell,
  protobuf,
  python,
  r,
  ruby,
  rust,
  scala,
  scss,
  shell,
  sql,
  swift,
  typescript,
  vbnet,
  x86asm,
  xml,
  yaml
}

// registerLanguage also registers the declared aliases (html→xml, md→markdown,
// txt→plaintext, toml→ini, proto→protobuf, js→javascript…), which is what the
// `hljs.getLanguage()` lookups in CodeViewer.vue rely on.
Object.entries(LANGUAGES).forEach(([name, language]) => hljs.registerLanguage(name, language))

const ESCAPE_MAP = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }

/**
 * Escapes user content for safe interpolation into highlighted markup.
 */
export function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"]/g, (char) => ESCAPE_MAP[char])
}

/**
 * markdown-it `highlight` option implementation.
 * Returning a string that starts with `<pre` makes markdown-it use it verbatim.
 *
 * Replaces `markdown-it-highlightjs`, which statically imports the FULL
 * highlight.js language pack into whichever chunk uses it.
 */
export function highlightCode(str, lang) {
  const language = lang || 'txt'
  try {
    const { value } = hljs.highlight(str, { language, ignoreIllegals: true })
    return `<pre><code class="hljs language-${language}">${value}</code></pre>`
  } catch (ex) {
    console.error('Error rendering markdown code block', { ex, lang })
  }
  return `<pre><code class="hljs language-${language}">${escapeHtml(str)}</code></pre>`
}

export default hljs