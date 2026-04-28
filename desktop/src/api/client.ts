import axios from "axios";

// Base URL is set once the Electron main process reports the server port
let _baseURL = "http://127.0.0.1:8000";

export function setBaseURL(port: number) {
  _baseURL = `http://127.0.0.1:${port}`;
  client.defaults.baseURL = _baseURL;
}

export function getBaseURL(): string {
  return _baseURL;
}

const client = axios.create({ baseURL: _baseURL, timeout: 30_000 });

export default client;
