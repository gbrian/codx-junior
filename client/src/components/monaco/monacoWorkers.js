/**
 * Monaco worker bootstrap.
 *
 * The worker modules used to be imported by `main.ts`, which put the whole
 * worker graph on the entry chunk's dependency list. They are now imported on
 * demand, right before the first editor is created.
 *
 * `MonacoEnvironment` must exist before Monaco instantiates its first editor,
 * otherwise it silently falls back to running the language services on the main
 * thread — the opposite of what we want.
 */
let workersReady = null

export function ensureMonacoWorkers() {
  if (workersReady) return workersReady

  workersReady = Promise.all([
    import('monaco-editor/esm/vs/editor/editor.worker?worker'),
    import('monaco-editor/esm/vs/language/json/json.worker?worker'),
    import('monaco-editor/esm/vs/language/css/css.worker?worker'),
    import('monaco-editor/esm/vs/language/html/html.worker?worker'),
    import('monaco-editor/esm/vs/language/typescript/ts.worker?worker')
  ]).then(([editorWorker, jsonWorker, cssWorker, htmlWorker, tsWorker]) => {
    self.MonacoEnvironment = {
      getWorker(_, label) {
        if (label === 'json') {
          return new jsonWorker.default()
        }
        if (label === 'css' || label === 'scss' || label === 'less') {
          return new cssWorker.default()
        }
        if (label === 'html' || label === 'handlebars' || label === 'razor') {
          return new htmlWorker.default()
        }
        if (label === 'typescript' || label === 'javascript') {
          return new tsWorker.default()
        }
        return new editorWorker.default()
      }
    }
    return self.MonacoEnvironment
  })

  return workersReady
}

export default ensureMonacoWorkers