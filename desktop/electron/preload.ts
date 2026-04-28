import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("electronAPI", {
  // Called once to get the port after server-ready fires
  getServerPort: (): Promise<number | null> =>
    ipcRenderer.invoke("get-server-port"),

  // Listen for server-ready event (fires after window loads)
  onServerReady: (callback: (port: number) => void) => {
    ipcRenderer.on("server-ready", (_event, { port }) => callback(port));
  },

  // Native file picker → returns absolute file path
  openFileDialog: (): Promise<string | null> =>
    ipcRenderer.invoke("open-file-dialog"),

  // User data directory (where storage/ lives in production)
  getUserDataPath: (): Promise<string> =>
    ipcRenderer.invoke("get-user-data-path"),

  // Open URL in default browser
  openExternal: (url: string) => ipcRenderer.send("open-external", url),
});

// Type declaration for TypeScript in renderer
declare global {
  interface Window {
    electronAPI: {
      getServerPort: () => Promise<number | null>;
      onServerReady: (callback: (port: number) => void) => void;
      openFileDialog: () => Promise<string | null>;
      getUserDataPath: () => Promise<string>;
      openExternal: (url: string) => void;
    };
  }
}
