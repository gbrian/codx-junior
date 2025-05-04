import axios from 'axios'


let interceptors = {
  request: [],
  response: []
}

class CodxJuniorConnection {
  constructor({ settings, user } = {}) {
    this.user = user
    this.settings = settings || {};    
  }

  get headers() {
    return {
      "x-sid": this.settings.sid,
      "Authentication": `Bearer ${this.user?.token}`
    };
  }

  createConnection() {
    this.axiosInstance = axios.create({});
    this.liveRequests = 0;

    this.axiosInstance.interceptors.request.use(...interceptors.request);
    this.axiosInstance.interceptors.response.use(...interceptors.response);
  }
  
  prepareUrl(url) {
    const query = `codx_path=${encodeURIComponent(this.settings?.codx_path)}`;
    if (url.indexOf("codx_path") === -1) {
      let [path, params] = url.split("?");
      if (params) {
        params += `&${query}`;
      } else {
        params = query;
      }
      url = `${path}?${params}`;
      return url;
    }
    return url;
  }

  get(url) {
    this.createConnection()
    this.liveRequests++;
    return this.axiosInstance.get(this.prepareUrl(url), { headers: this.headers })
      .then(({ data }) => data)
      .finally(() => this.liveRequests--);
  }

  del(url) {
    this.createConnection()
    this.liveRequests++;
    return this.axiosInstance.delete(this.prepareUrl(url), { headers: this.headers })
      .finally(() => this.liveRequests--);
  }

  post(url, data) {
    this.createConnection()
    this.liveRequests++;
    return this.axiosInstance.post(this.prepareUrl(url), data, { headers: this.headers })
      .then(({ data }) => data)
      .finally(() => this.liveRequests--);
  }

  put(url, data) {
    this.createConnection()
    this.liveRequests++;
    return this.axiosInstance.put(this.prepareUrl(url), data, { headers: this.headers })
          .then(({ data }) => data)
          .finally(() => this.liveRequests--);
  }
}

const initializeAPI = (project) => {
  const API = {
    sid: "",
    connection: null,
    _user: null,
    get user () {
      return API._user
    },
    set user(user) {
      API._user = user
      API.initConnection()
    },
    _activeProject: project,
    get activeProject() {
      return this._activeProject
    },
    set activeProject(value) {
      this._activeProject = value
      API.initConnection()
    },
    get headers() {
      return {
        "x-sid": API.sid,
        "Authentication": `Bearer ${API.user?.token}`
      };
    },
    set interceptors(value) {
      interceptors = value
    },
    initConnection() {
      API.connection = new CodxJuniorConnection({
        settings: API.activeProject,
        user: API.user
      })
    },
    get(url) {
      return API.connection.get(url)
    },
    del(url) {
      return API.connection.del(url)
    },
    post(url, data) {
      return API.connection.post(url, data)
    },
    put(url, data) {
      return API.connection.put(url, data)
    },
    users: {
      async list() {
        API.userNetwork = await API.get('/api/users');
      },
      async login(user) {
        if (!user) {
          try {
            user = API.user = JSON.parse(localStorage.getItem("CODX_USER"))
            API.initConnection()
          }catch{}
          if (!user) {
            return null
          } 
        }
        const data = await API.post('/api/users/login', user);
        API.user = data;
        localStorage.setItem("CODX_USER", JSON.stringify(API.user))
        await API.onUserLogin()
        return data;
      },
      async save(user) {
        const data = await API.put('/api/users', user);
        API.user = data;
        localStorage.setItem("CODX_USER", JSON.stringify(API.user))
        return data;
      },
      async logout() {
        API.user = null;
        API.activeProject = {}
        localStorage.removeItem("CODX_USER")
      }
    },
    apps: {
      async list() {
        const apps = await API.get('/api/apps');
        return apps;
      },
      async run(appName) {
        const data = await API.get(`/api/apps/run?app=${appName}`);
        return data;
      }
    },
    async project(projectOrId) {
      if (!projectOrId.codx_path) {
        projectOrId = API.allProjects.find(p => p.id === projectOrId || p.project_name === projectOrId) 
      }
      if (projectOrId.codx_path === API.settings.codx_path) {
        return API
      }
      return initializeAPI(projectOrId)
    },
    projects: {
      async list() {
        const data = await API.get('/api/projects');
        API.allProjects = data;
        return API.allProjects;
      },
      create(projectPath) {
        return API.post('/api/projects?project_path=' + encodeURIComponent(projectPath), {});
      },
      delete() {
        localStorage.setItem("API_SETTINGS", "");
        API.del('/api/projects');
        API.activeProject = null;
      },
      async readme() {
        const data = await API.get('/api/projects/readme');
        return data;
      },
      watch() {
        return API.get('/api/project/watch');
      },
      unwatch() {
        return API.get('/api/project/unwatch');
      },
      test() {
        return API.get('/api/project/script/test');
      },
      async branches() {
        const branches = await API.get('/api/projects/repo/branches');
        return branches;
      }
    },
    settings: {
      async read() {
        const data = await API.get('/api/settings');
        API.activeProject = { ...API.activeProject || {}, ...data };
        if (API.activeProject) {
          localStorage.setItem("API_SETTINGS", JSON.stringify(data));
        }
        return data;
      },
      async save(settings) {
        await API.put('/api/settings?', settings || API.activeProject);
        return API.settings.read();
      },
      global: {
        async read() {
          const data = await API.get('/api/global/settings');
          API.globalSettings = data;
          return data;
        },
        async write(settings) {
          await API.post('/api/global/settings', settings);
          return API.settings.global.read();
        }
      }
    },
    knowledge: {
      status() {
        return API.get('/api/knowledge/status');
      },
      reload() {
        return API.get('/api/knowledge/reload');
      },
      reloadFolder(path) {
        return API.post(`/api/knowledge/reload-path`, { path });
      },
      search({
        searchTerm: search_term,
        searchType: search_type,
        documentSearchType: document_search_type,
        cutoffScore: document_cutoff_score,
        cutoffRag: document_cutoff_rag,
        documentCount: document_count
      }) {
        return API.post(`/api/knowledge/reload-search`, {
          search_term,
          search_type,
          document_search_type,
          document_cutoff_score,
          document_cutoff_rag,
          document_count
        });
      },
      delete(sources) {
        return API.post(`/api/knowledge/delete`, { sources });
      },
      deleteAll() {
        return API.del(`/api/knowledge/delete`);
      },
      keywords() {
        return API.get(`/api/knowledge/keywords`);
      },
      searchKeywords(searchQuery) {
        return API.get(`/api/knowledge/keywords?query=${searchQuery}`);
      }
    },
    chats: {
      stream() {
        return API.get('/api/stream');
      },
      async list() {
        const data = await API.get('/api/chats');
        return data;
      },
      async loadChat({ id, file_path }) {
        const data = await API.get(`/api/chats?file_path=${file_path || ''}&id=${id || ''}`);
        return data;
      },
      async newChat() {
        return {
          id: new Date().getTime(),
          name: "New chat"
        };
      },
      async message(chat) {
        return API.post('/api/chats?', chat);
      },
      async fromUrl(chat) {
        return API.post('/api/chats/from-url?', chat);
      },
      async subTasks(chat) {
        return API.post('/api/chats/sub-tasks?', chat);
      },
      save(chat) {
        return API.put(`/api/chats?chatonly=0`, chat);
      },
      saveChatInfo(chat) {
        return API.put(`/api/chats?chatonly=1`, chat);
      },
      delete(chat) {
        return API.del(`/api/chats?chat_id=${chat.id}`);
      },
      kanban: {
        async load() {
          const kanban = await API.get('/api/kanban');
          return kanban;
        },
        async save(kanban) {
          API.post('/api/kanban', kanban);
        }
      }
    },
    run: {
      improve(chat) {
        return API.post('/api/run/improve?', chat);
      },
      patch(aiCodeGenerator) {
        return API.post('/api/run/improve/patch?', aiCodeGenerator).then(({ data }) => data);
      },
      edit(chat) {
        return API.post('/api/run/edit?', chat);
      },
      liveEdit({ chat, html, url, message }) {
        return API.post('/api/run/live-edit?', { chat_name: chat.name, html, url, message });
      },
      changesSummary({ branch, rebuild }) {
        return API.get(`/api/run/changes/summary?branch=${branch}&refresh=${rebuild}`).then(({ data }) => data);
      }
    },
    profiles: {
      list() {
        return API.get('/api/profiles');
      },
      load(name) {
        return API.get(`/api/profiles/${name}`);
      },
      save(profile) {
        return API.post(`/api/profiles`, profile);
      },
      async delete(name) {
        await API.del(`/api/profiles/${name}`);
      }
    },
    coder: {
      openFile(file) {
        API.get(`/api/code-server/file/open?file_name=${encodeURIComponent(file)}`);
      }
    },
    images: {
      async upload(file) {
        let formData = new FormData();
        formData.append("file", file);
        const url = await API.post(`/api/images`, formData);
        return window.location.origin + url;
      }
    },
    wiki: {
      read(path) {
        return API.get(`/api/wiki?file_path=${path}`);
      }
    },
    engine: {
      update() {
        return API.get('/api/update');
      }
    },
    browser: {
      message(chat) {
        return API.post('/api/browser', chat);
      },
    },
    tools: {
      async imageToText(file) {
        const formData = new FormData();
        formData.append("file", file);
        return (await API.post(`/api/image-to-text`, formData)).data;
      }
    },
    async onUserLogin() {
      API.allProjects = await API.projects.list()
      try {
        const activeProject = JSON.parse(localStorage.getItem("API_SETTINGS"))
        API.activeProject = API.allProjects.find(p => p.project_id === activeProject.project_id)
      } catch {}
      if (!API.activeProject && API.allProjects.length) {
        API.activeProject = API.allProjects[0]
      }
      await Promise.all([
        API.screen.getScreenResolution(),
        API.settings.global.read(),
        API.users.list()
      ])
    },
    async setActiveProject({ project_id }) {
      if (project_id !== API.activeProject?.project_id) {
        API.activeProject = API.allProjects?.find(p => p.project_id === project_id)
        await API.settings.read()
      }
      return API
    },
    logs: {
      async read(logName, size) {
        return API.get(`/api/logs/${logName}?log_size=${size}`);
      },
      async list() {
        return API.get('/api/logs');
      }
    },
    files: {
      list(path) {
        return API.get(`/api/files?path=${path}`);
      },
      read(path) {
        return API.get(`/api/files/read?path=${path}`);
      },
      search(search) {
        return API.get(`/api/files/find?search=${search}`);
      },
      write(source, page_content) {
        return API.post(`/api/files/write?path=${source}`, { page_content, metadata: { source } });
      }
    },
    screen: {
      display: null,
      async setScreenResolution(resolution) {
        await API.post('/api/screen', { resolution });
        return API.screen.getScreenResolution();
      },
      async getScreenResolution() {
        const display = await API.get('/api/screen');
        API.screen.display = display;
        return API.screen.display;
      }
    },
    async restart() {
      await API.post("/api/restart");
      let waitTime = 3;
      return new Promise((ok, ko) => {
        const ix = setInterval(async () => {
          if (--waitTime) {
            try {
              await API.init();
              clearInterval(ix);
              ok();
            } catch { }
          } else {
            clearInterval(ix);
            ko();
          }
        }, 5000);
      });
    },
    get permissions () {
      const permissions = API.activeProject?.permissions || []
      const isAdmin = API.user?.role === 'admin'
      const isProjectAdmin = permissions.includes("admin")
      return {
        isAdmin,
        isProjectAdmin
      }
    }
  };
  API.initConnection()
  return API;
};

export const API = initializeAPI()