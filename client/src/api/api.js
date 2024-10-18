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
});
export const API = {
  axiosRequest,
  liveRequests: 0,
  get (url) {
    API.liveRequests++
    return axiosRequest.get(prepareUrl(url))
      .catch(console.error)
      .finally(() => API.liveRequests--)
  },
  del (url) {
    API.liveRequests++
    return axiosRequest.delete(prepareUrl(url))
      .catch(console.error)
      .finally(() => API.liveRequests--)
  },
  post (url, data) {
    API.liveRequests++
    return axiosRequest.post(prepareUrl(url), data)
    .catch(console.error)
    .finally(() => API.liveRequests--)
  },
  put (url, data) {
    API.liveRequests++
    return axiosRequest.put(prepareUrl(url), data)
    .catch(console.error)
    .finally(() => API.liveRequests--)
  },
  lastSettings: {},
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
      API.lastSettings = res.data
      if (API.lastSettings) {
        localStorage.setItem("API_SETTINGS", JSON.stringify(API.lastSettings))
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
      read() {
        return API.get('/api/global/settings')
      },
      write(settings) {
        return API.post('/api/global/settings', settings)
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
    async list () {
      const { data } = await API.get('/api/chats')
      return data
    },
    async loadChat (name) {
      const { data } = await API.get(`/api/chats?chat_name=${name}`)
      return data
    },
    async newChat () {
      return {
        id: new Date().getTime(),
        name: "New chat"
      }
    },
    async message (chat) {
      const { data: message } = await API.post('/api/chats?', chat)
      chat.messages.push(message)
      return chat
    },
    save (chat) {
      return API.put(`/api/chats?chatonly=0`, chat)
    },
    saveChatInfo(chat) {
      return API.put(`/api/chats?chatonly=1`, chat)
    },
    delete(chatName) {
      return API.del(`/api/chats?chat_name=${chatName}`)
    }
  },
  run: {
    improve (chat) {
      return API.post('/api/run/improve?', chat)
    },
    edit (chat) {
      return API.post('/api/run/edit?', chat)
    },
    liveEdit ({ chat, html, url, message }) {
      return API.post('/api/run/live-edit?', { chat_name: chat.name, html, url, message })
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
      let formData = new FormData();
      formData.append("file", file);
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
  tools: {
    async imageToText (file) {
      const formData = new FormData();
      formData.append("file", file);
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
    }
    API.liveRequests--
    console.log("API init", codx_path, API.lastSettings)
  }
}
const codx_path = decodeURIComponent(codx_key ? codx_key[1] : "")
API.init(codx_path)
window.API = API