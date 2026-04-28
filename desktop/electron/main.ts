import {
  app,
  BrowserWindow,
  ipcMain,
  dialog,
  shell,
  nativeTheme,
} from "electron";
import { join } from "path";
import { spawn, ChildProcess } from "child_process";
import * as net from "net";
import * as fs from "fs";

let mainWindow: BrowserWindow | null = null;
let serverProcess: ChildProcess | null = null;
let serverPort: number | null = null;

// ── Port discovery ────────────────────────────────────────────────────────────
function findFreePort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.listen(0, "127.0.0.1", () => {
      const port = (server.address() as net.AddressInfo).port;
      server.close(() => resolve(port));
    });
    server.on("error", reject);
  });
}

// ── Python server ─────────────────────────────────────────────────────────────
function getServerBinary(): { bin: string; args: string[] } {
  const isProd = app.isPackaged;

  if (isProd) {
    const ext = process.platform === "win32" ? ".exe" : "";
    const bin = join(
      process.resourcesPath,
      "server",
      `rally-coach-server${ext}`
    );
    return { bin, args: [] };
  }

  // Dev: run uvicorn from repo root
  const repoRoot = join(__dirname, "..", "..", "..");
  return {
    bin: "python3",
    args: ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1"],
  };
}

async function startServer(): Promise<number> {
  const port = await findFreePort();
  const { bin, args } = getServerBinary();

  const repoRoot = app.isPackaged
    ? join(process.resourcesPath, "server")
    : join(__dirname, "..", "..", "..");

  serverProcess = spawn(bin, [...args, "--port", String(port)], {
    cwd: repoRoot,
    env: {
      ...process.env,
      PORT: String(port),
      STORAGE_DIR: join(app.getPath("userData"), "storage"),
    },
  });

  serverProcess.stdout?.on("data", (d) =>
    console.log("[server]", d.toString().trim())
  );
  serverProcess.stderr?.on("data", (d) =>
    console.error("[server]", d.toString().trim())
  );
  serverProcess.on("exit", (code) => {
    console.log(`[server] exited with code ${code}`);
  });

  // Poll until the server responds
  await waitForServer(port);
  return port;
}

function waitForServer(port: number, timeout = 30_000): Promise<void> {
  const start = Date.now();
  return new Promise((resolve, reject) => {
    const check = () => {
      const client = net.createConnection({ port, host: "127.0.0.1" });
      client.on("connect", () => {
        client.destroy();
        resolve();
      });
      client.on("error", () => {
        if (Date.now() - start > timeout) {
          reject(new Error("Server startup timed out"));
        } else {
          setTimeout(check, 500);
        }
      });
    };
    check();
  });
}

// ── Window ────────────────────────────────────────────────────────────────────
function createWindow(port: number) {
  nativeTheme.themeSource = "dark";

  mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 900,
    minHeight: 600,
    titleBarStyle: "hiddenInset",
    backgroundColor: "#0f1117",
    webPreferences: {
      preload: join(__dirname, "../preload/index.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  if (app.isPackaged) {
    mainWindow.loadFile(join(__dirname, "../renderer/index.html"));
  } else {
    // electron-vite dev server
    mainWindow.loadURL("http://localhost:5173");
    mainWindow.webContents.openDevTools();
  }

  mainWindow.webContents.on("did-finish-load", () => {
    mainWindow!.webContents.send("server-ready", { port });
  });

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

// ── IPC handlers ──────────────────────────────────────────────────────────────
ipcMain.handle("get-server-port", () => serverPort);

ipcMain.handle("open-file-dialog", async () => {
  const result = await dialog.showOpenDialog({
    properties: ["openFile"],
    filters: [
      { name: "Video Files", extensions: ["mp4", "mov", "avi", "m4v", "mkv"] },
    ],
  });
  return result.canceled ? null : result.filePaths[0];
});

ipcMain.handle("get-user-data-path", () => app.getPath("userData"));

ipcMain.on("open-external", (_event, url: string) => {
  shell.openExternal(url);
});

// ── App lifecycle ─────────────────────────────────────────────────────────────
app.whenReady().then(async () => {
  try {
    console.log("Starting Rally Coach server...");
    serverPort = await startServer();
    console.log(`Server ready on port ${serverPort}`);
    createWindow(serverPort);
  } catch (err) {
    console.error("Failed to start server:", err);
    dialog.showErrorBox(
      "Rally Coach — Startup Error",
      `Failed to start the analysis server:\n\n${err}\n\nPlease ensure Python 3.11+ and all dependencies are installed.`
    );
    app.quit();
  }
});

app.on("window-all-closed", () => {
  serverProcess?.kill();
  if (process.platform !== "darwin") app.quit();
});

app.on("activate", () => {
  if (mainWindow === null && serverPort !== null) {
    createWindow(serverPort);
  }
});

app.on("before-quit", () => {
  serverProcess?.kill();
});
