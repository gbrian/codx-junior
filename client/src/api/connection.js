import axios from 'axios'


const interceptors = {
  request: [],
  response: []
}

export class CodxJuniorConnection {
  constructor({ settings, user } = {}) {
    this.user = user
    this.settings = settings || {};    
    this.interceptors = interceptors
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

  delete(url) {
    this.createConnection()
    this.liveRequests++;
    return this.axiosInstance.delete(this.prepareUrl(url), { headers: this.headers })
          .then(({ data }) => data)
          .finally(() => this.liveRequests--);
  }
}