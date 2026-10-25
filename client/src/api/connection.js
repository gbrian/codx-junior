import axios from 'axios'
import { beginNetworkCall } from './telemetry'


const interceptors = {
  request: [],
  response: []
}

export class CodxJuniorConnection {
  constructor({ settings, user } = {}) {
    this.user = user
    this.settings = settings || {}
    // Socket.IO session id associated with the current socket. It is kept in
    // sync by the API layer (see api.js `initSocket` / `initConnection`) and
    // sent as `x-sid` so the meets API can target signalling at *this* session
    // instead of every device logged in with the same account.
    this.sid = this.settings.sid || ''
    this.interceptors = interceptors
  }

  get headers() {
    return {
      "x-sid": this.sid || this.settings?.sid || '',
      "x-username": this.user?.username || '',
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

  /**
   * Feeds the client-side "Local network" log of API monitoring and returns the
   * SAME promise, so the request chain is untouched.
   *
   * The entry is opened BEFORE the request settles (`beginNetworkCall`), which
   * is what makes the in-flight count and the chart's "processing" series real;
   * `finish()` closes it with the status and the wall-clock latency the browser
   * measured (DNS + TCP + round trip) — the part the server-side aggregates
   * cannot see. Bodies and responses never leave the request.
   *
   * @param {string} method
   * @param {string} url
   * @param {Promise} request
   * @returns {Promise} the same promise
   */
  trackLocalCall(method, url, request) {
    const call = beginNetworkCall({ method, url })
    // Not a local/LAN target: nothing to record, keep the chain untouched.
    if (!call) return request

    request.then(
      (response) => call.finish({ status: response?.status }),
      (error) => call.finish({ status: error?.response?.status, error })
    )

    return request
  }

  get(url) {
    this.createConnection()
    this.liveRequests++;
    const request = this.axiosInstance.get(this.prepareUrl(url), { headers: this.headers })
    return this.trackLocalCall('GET', url, request)
      .then(({ data }) => data)
      .finally(() => this.liveRequests--);
  }

  del(url) {
    this.createConnection()
    this.liveRequests++;
    const request = this.axiosInstance.delete(this.prepareUrl(url), { headers: this.headers })
    return this.trackLocalCall('DELETE', url, request)
      .finally(() => this.liveRequests--);
  }

  post(url, data) {
    this.createConnection()
    this.liveRequests++;
    const request = this.axiosInstance.post(this.prepareUrl(url), data, { headers: this.headers })
    return this.trackLocalCall('POST', url, request)
      .then(({ data }) => data)
      .finally(() => this.liveRequests--);
  }

  put(url, data) {
    this.createConnection()
    this.liveRequests++;
    const request = this.axiosInstance.put(this.prepareUrl(url), data, { headers: this.headers })
    return this.trackLocalCall('PUT', url, request)
          .then(({ data }) => data)
          .finally(() => this.liveRequests--);
  }

  delete(url) {
    this.createConnection()
    this.liveRequests++;
    const request = this.axiosInstance.delete(this.prepareUrl(url), { headers: this.headers })
    return this.trackLocalCall('DELETE', url, request)
          .finally(() => this.liveRequests--);
  }
}