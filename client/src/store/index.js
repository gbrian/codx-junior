import { createStore, Store } from 'vuex'
import {
  useAccessor,
} from 'typed-vuex'
import { API } from '../api/api'

import * as session from './session'
import * as projects from './project'
import * as ui from './ui'
import * as users from './users'
import * as profiles from './profiles'
import * as logs from './logs'
import * as chats from './chats'
import * as teams from './teams'
import * as media from './media'
import * as views from './views'

const modules = { session, projects, ui, users, profiles, logs, chats, teams, media, views }
const storePattern = {
  state () {
    return {
    }
  },
  modules,
}


let store = null
let storex = null
store = createStore(storePattern)
storex = useAccessor(store, storePattern)
storex.init = async () => {
  await Promise.all(Object.keys(modules).map(async m => {
    if (storex[m].init) {
      await storex[m].init(storex)
    }
  }))
}
storex.store = store
storex.api = API

export default storex.store
export const $storex = storex

// Map of file extensions to Monaco language identifiers
export const EXTENSION_LANGUAGE_MAP = {
  js: 'javascript',
  jsx: 'javascript',
  mjs: 'javascript',
  cjs: 'javascript',
  ts: 'typescript',
  tsx: 'typescript',
  py: 'python',
  rb: 'ruby',
  java: 'java',
  kt: 'kotlin',
  kts: 'kotlin',
  cs: 'csharp',
  cpp: 'cpp',
  cc: 'cpp',
  cxx: 'cpp',
  c: 'c',
  h: 'c',
  hpp: 'cpp',
  go: 'go',
  rs: 'rust',
  php: 'php',
  swift: 'swift',
  scala: 'scala',
  r: 'r',
  dart: 'dart',
  lua: 'lua',
  pl: 'perl',
  pm: 'perl',
  sh: 'shell',
  bash: 'shell',
  zsh: 'shell',
  ps1: 'powershell',
  psm1: 'powershell',
  html: 'html',
  htm: 'html',
  xml: 'xml',
  svg: 'xml',
  css: 'css',
  scss: 'scss',
  sass: 'scss',
  less: 'less',
  json: 'json',
  jsonc: 'json',
  yaml: 'yaml',
  yml: 'yaml',
  toml: 'ini',
  ini: 'ini',
  env: 'ini',
  md: 'markdown',
  mermaid: 'markdown',
  mdx: 'markdown',
  sql: 'sql',
  graphql: 'graphql',
  gql: 'graphql',
  proto: 'proto',
  tf: 'hcl',
  hcl: 'hcl',
  vue: 'html',
  svelte: 'html',
  dockerfile: 'dockerfile',
  makefile: 'makefile',
  gradle: 'groovy',
  groovy: 'groovy',
  ex: 'elixir',
  exs: 'elixir',
  erl: 'erlang',
  hrl: 'erlang',
  clj: 'clojure',
  cljs: 'clojure',
  fs: 'fsharp',
  fsx: 'fsharp',
  vb: 'vb',
  asm: 'asm',
  s: 'asm',
}

window.$storex = $storex