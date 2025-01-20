import axios from 'axios'

const codx_key = window.location.search
                    .slice(1).split("&")
                    .map(p => p.split("="))
                    .find(([k]) => k === "codx_path")

const query = () => `codx_path=${encodeURIComponent(API.lastSettings?.codx_path)}`
const prepareUrl = (url) => {
  if (url.indexOf("codx_path") === -1) {
    let [path, params] = url.split("?")
    if (params) {
      params += `&${query()}`
    } else {
      params = query()
    }
    url =`${path}?${params}`
    return url
  }
  return url
}

const axiosRequest = axios.create({
})
export const API = {
  sid: "",
  axiosRequest,
  liveRequests: 0,
  get headers () {
    return {
      "x-sid": API.sid
    }
  },
  get (url) {
    API.liveRequests++
    return axiosRequest.get(prepareUrl(url), { headers: API.headers })
      .catch(console.error)
      .finally(() => API.liveRequests--)
  },
  del (url) {
    API.liveRequests++
    return axiosRequest.delete(prepareUrl(url), { headers: API.headers })
      .catch(console.error)
      .finally(() => API.liveRequests--)
  },
  post (url, data) {
    API.liveRequests++
    return axiosRequest.post(prepareUrl(url), data, { headers: API.headers })
    .catch(console.error)
    .finally(() => API.liveRequests--)
  },
  put (url, data) {
    API.liveRequests++
    return axiosRequest.put(prepareUrl(url), data, { headers: API.headers })
    .catch(console.error)
    .finally(() => API.liveRequests--)
  },
  lastSettings: {},
  apps: {
    async list(){
      const { data: apps } = await API.get('/api/apps')
      return apps
    },
    async run(appName){
      const { data } = await API.get(`/api/apps/run?app=${appName}`)
      return data
    } 
  },
  project: {
    async list () {
      const res = await API.get('/api/projects')
      if (API.lastSettings) {
        API.allProjects = res.data
      }
      return res
    },
    create(projectPath) {
      return API.post('/api/projects?project_path=' + encodeURIComponent(projectPath), {})
    },
    delete() {
      localStorage.setItem("API_SETTINGS", "")
      API.del('/api/projects')
      API.lastSettings = null
    },
    async readme () {
      const { data } = await API.get('/api/projects/readme')
      return data
    },
    watch () {
      return API.get('/api/project/watch')
    },
    unwatch () {
      return API.get('/api/project/unwatch')
    },
    test () {
      return API.get('/api/project/script/test')
    }
  },
  settings: {
    async read () {
      const res = await API.get('/api/settings')
      API.lastSettings = { ...API.lastSettings || {}, ...res.data }
      if (API.lastSettings) {
        localStorage.setItem("API_SETTINGS", JSON.stringify(res.data))
      }
      return res
    },
    write (settings) {
      return API.put('/api/settings?', settings)
    },
    async save() {
      await API.put('/api/settings?', API.lastSettings)
      return API.settings.read()
    },
    global: {
      async read() {
        const { data } = await API.get('/api/global/settings')
        API.globalSettings = data
        return { data }
      },
      async write(settings) {
        await API.post('/api/global/settings', settings)
        return API.global.read()
      }
    }
  },
  knowledge: {
    status () {
      return API.get('/api/knowledge/status')
    },
    reload () {
      return API.get('/api/knowledge/reload')
    },
    reloadFolder (path) {
      return API.post(`/api/knowledge/reload-path`, { path })
    },
    search ({ 
        searchTerm: search_term,
        searchType: search_type,
        documentSearchType: document_search_type,
        cutoffScore: document_cutoff_score,
        documentCount: document_count
    }) {
      return API.post(`/api/knowledge/reload-search`, {
          search_term,
          search_type,
          document_search_type,
          document_cutoff_score,
          document_count
      })
    },
    delete (sources) {
      return API.post(`/api/knowledge/delete`, { sources })  
    },
    deleteAll() {
      return API.del(`/api/knowledge/delete`)  
    },
    keywords() {
      return API.get(`/api/knowledge/keywords`)
    },
    searchKeywords (searchQuery) {
      return API.get(`/api/knowledge/keywords?query=${searchQuery}`)
    }
  },
  chats: {
    stream() {
      return API.get('/api/stream')
    },
    async list () {
      const { data } = await API.get('/api/chats')
      return data
    },
    async loadChat ({ file_path }) {
      const { data } = await API.get(`/api/chats?file_path=${file_path}`)
      return data
    },
    async newChat () {
      return {
        id: new Date().getTime(),
        name: "New chat"
      }
    },
    async message (chat) {
      return API.post('/api/chats?', chat)
    },
    save (chat) {
      return API.put(`/api/chats?chatonly=0`, chat)
    },
    saveChatInfo(chat) {
      return API.put(`/api/chats?chatonly=1`, chat)
    },
    delete(board, chatName) {
      return API.del(`/api/chats?board=${board}&chat_name=${chatName}`)
    },
    boards: {
      async load() {
        const { data: boards } = await API.get('/api/boards')
        return boards
      },
      async save(boards) {
        API.post('/api/boards', boards)
      }
    }
  },
  run: {
    improve (chat) {
      return API.post('/api/run/improve?', chat)
    },
    patch (aiCodeGenerator) {
      return API.post('/api/run/improve/patch?', aiCodeGenerator).then(({ data}) => data)
    },
    edit (chat) {
      return API.post('/api/run/edit?', chat)
    },
    liveEdit ({ chat, html, url, message }) {
      return API.post('/api/run/live-edit?', { chat_name: chat.name, html, url, message })
    },
    changesSummary(rebuild) {
      return API.get(`/api/run/changes/summary?refresh=${rebuild}`).then(({ data}) => data)      
    }
  },
  profiles: {
    list () {
      return API.get('/api/profiles')
    },
    load (name) {
      return API.get(`/api/profiles/${name}`)
    },
    save (profile) {
      return API.post(`/api/profiles`, profile)
    },
    async delete (name) {
      await API.del(`/api/profiles/${name}`)
      API.lastSettings = null
    }
  },
  coder: {
    openFile(file) {
      API.get(`/api/code-server/file/open?file_name=${encodeURIComponent(file)}`)
    }
  },
  images: {
    async upload (file) {
      let formData = new FormData()
      formData.append("file", file)
      const { data: url } = await API.post(`/api/images`, formData)
      return window.location.origin + url
    }
  },
  wiki: {
    read (path) {
      return API.get(`/api/wiki?file_path=${path}`)
    }
  },
  engine: {
    update () {
      return API.get('/api/update')
    }
  },
  browser: {
    message (chat) {
      return API.post('/api/browser', chat)
    },
  },
  tools: {
    async imageToText (file) {
      const formData = new FormData()
      formData.append("file", file)
      return (await API.post(`/api/image-to-text`, formData)).data
    }
  },
  async init (codx_path) {
    API.liveRequests++
    this.codx_path = codx_path
    if (codx_path) {
      const { data: projects } = await API.project.list()
      API.lastSettings = projects.find(p => p.codx_path === codx_path)
      if (API.lastSettings) {
        await API.settings.read()
        localStorage.setItem("API_CODX_PATH", API.lastSettings.codx_path)
      }
      API.allProjects = projects
    } else {
      const codx_path = localStorage.getItem("API_CODX_PATH")
      try {
        const { data: projects } = await API.project.list()
        API.allProjects = projects
        API.lastSettings = projects.find(p => p.codx_path === codx_path) ||
                              projects[0]
      } catch (ex) {
        console.error("Invalid settings")
      }
      API.screen.getScreenResolution()
    }
    API.liveRequests--
    await API.settings.global.read()
    console.log("API init", codx_path, API)
  },
  logs: {
    async read(logName, size) {
      return API.get(`/api/logs/${logName}?log_size=${size}`)
    },
    async list() {
      return API.get('/api/logs')
    }
  },
  files: {
    list (path) {
      return API.get(`/api/files?path=${path}`)
    },
    read (path) {
      return API.get(`/api/files/read?path=${path}`)
    },
    search (search) {
      return API.get(`/api/files/find?search=${search}`)
    },
    write (source, page_content) {
      return API.post(`/api/files/write?path=${source}`, { page_content, metadata: { source } } )
    }
  },
  screen: {
    display: null,
    async setScreenResolution (resolution) {
      await API.post('/api/screen', { resolution })
      return API.screen.getScreenResolution()
    },
    async getScreenResolution () {
      const { data: display } = await API.get('/api/screen') 
      API.screen.display = display
      return API.screen.display
    }
  },
  async restart () {
    await API.post("/api/restart")
    let waitTime = 3
    return new Promise((ok, ko) => {
      const ix = setInterval(async () => {
        if (--waitTime) {
          try {
            await API.init()
            clearInterval(ix)
            ok()
          } catch {}
        } else {
          clearInterval(ix)
          ko()
        }
      }, 5000)
    })
  }
}
window.API = API