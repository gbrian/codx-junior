import axios from 'axios'

const gpteng_key = window.location.search
                    .slice(1).split("&")
                    .map(p => p.split("="))
                    .find(([k]) => k === "gpteng_path")

const query = () => `gpteng_path=${encodeURIComponent(API.lastSettings?.gpteng_path)}`
const axiosRequest = axios.create({
});
export const API = {
  axiosRequest,
  liveRequests: 0,
  get (url) {
    API.liveRequests++
    return axiosRequest.get(url)
      .catch(console.error)
      .finally(() => API.liveRequests--)
  },
  del (url) {
    API.liveRequests++
    return axiosRequest.delete(url)
      .catch(console.error)
      .finally(() => API.liveRequests--)
  },
  post (url, data) {
    API.liveRequests++
    return axiosRequest.post(url, data)
    .catch(console.error)
    .finally(() => API.liveRequests--)
  },
  put (url, data) {
    API.liveRequests++
    return axiosRequest.put(url, data)
    .catch(console.error)
    .finally(() => API.liveRequests--)
  },
  lastSettings: {},
  project: {
    list () {
      return API.get('/api/projects')
    },
    create(projectPath) {
      return API.post('/api/projects?project_path=' + projectPath, {})
    },
    delete() {
      return API.del('/api/projects?' + query())
    },
    watch () {
      return API.get('/api/project/watch?' + query())
    },
    unwatch () {
      return API.get('/api/project/unwatch?' + query())
    },
    test () {
      return API.get('/api/project/script/test?' + query())
    }
  },
  settings: {
    async read () {
      const res = await API.get('/api/settings?' + query())
      API.lastSettings = res.data
      if (API.lastSettings) {
        localStorage.setItem("API_SETTINGS", JSON.stringify(API.lastSettings))
      }
      return res
    },
    write (settings) {
      return API.put('/api/settings?' + query(), settings)
    }
  },
  knowledge: {
    status () {
      return API.get('/api/knowledge/status?' + query())
    },
    reload () {
      return API.get('/api/knowledge/reload?' + query())
    },
    reloadFolder (path) {
      return API.post(`/api/knowledge/reload-path?` + query(), { path })
    },
    search ({ 
        searchTerm: search_term,
        searchType: search_type,
        documentSearchType: document_search_type,
        cutoffScore: document_cutoff_score,
        documentCount: document_count
    }) {
      return API.post(`/api/knowledge/reload-search?` + query(), {
          search_term,
          search_type,
          document_search_type,
          document_cutoff_score,
          document_count
      })
    },
    delete (sources) {
      return API.post(`/api/knowledge/delete?` + query(), { sources })  
    },
    keywords() {
      return API.get(`/api/knowledge/keywords?` + query())
    },
    searchKeywords (searchQuery) {
      return API.get(`/api/knowledge/keywords?query=${searchQuery}&` + query())
    }
  },
  chats: {
    async list () {
      const { data } = await API.get('/api/chats?' + query())
      return data
    },
    async loadChat (name) {
      const { data } = await API.get(`/api/chats?chat_name=${name}&` + query())
      return data
    },
    async newChat () {
      return {
        id: new Date().getTime(),
        name: "New chat"
      }
    },
    async message (chat) {
      const { data: message } = await API.post('/api/chats?' + query(), chat)
      chat.messages.push(message)
      return chat
    },
    save (chat, chatInfoOnly) {
      return API.put(`/api/chats?chatonly=${chatInfoOnly ? 1 : 0}&` + query(), chat)
    },
    delete(chatName) {
      return API.del(`/api/chats?chat_name=${chatName}&` + query())
    }
  },
  run: {
    improve (chat) {
      return API.post('/api/run/improve?' + query(), chat)
    },
    edit (chat) {
      return API.post('/api/run/edit?' + query(), chat)
    },
    liveEdit ({ chat, html, url, message }) {
      return API.post('/api/run/live-edit?' + query(), { chat_name: chat.name, html, url, message })
    }
  },
  profiles: {
    list () {
      return API.get('/api/profiles?' + query())
    },
    load (name) {
      return API.get(`/api/profiles/${name}?` + query())
    },
    save (profile) {
      return API.post(`/api/profiles?` + query(), profile)
    },
    async delete (name) {
      await API.delete(`/api/profiles/${name}?` + query())
      API.lastSettings = null
    }
  },
  images: {
    async upload (file) {
      let formData = new FormData();
      formData.append("file", file);
      const { data: url } = await API.post(`/api/images?` + query(), formData)
      return window.location.origin + url
    }
  },
  wiki: {
    read (path) {
      return API.get(`/api/wiki?file_path=${path}&` + query())
    }
  },
  engine: {
    update () {
      return API.get('/api/update?' + query())
    }
  },
  async init (gpteng_path) {
    this.gpteng_path = gpteng_path
    if (gpteng_path) {
      const { data } = await API.project.list()
      API.lastSettings = data.find(p => p.gpteng_path === gpteng_path)
    } else {
      const settings = localStorage.getItem("API_SETTINGS")
      try {
        API.lastSettings = JSON.parse(settings)
      } catch (ex) {
        console.error("Invalid settings")
      }
    }
    console.log("API init", gpteng_path, API.lastSettings)
  }
}
const gpteng_path = decodeURIComponent(gpteng_key ? gpteng_key[1] : "")
API.init(gpteng_path)
window.API = API