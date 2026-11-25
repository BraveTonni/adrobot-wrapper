import { spawn } from "node:child_process";
import { readFile } from "node:fs/promises";

async function main() {
  const passwordFile = process.env.FRONTEND_AUTH_PASSWORD_FILE;
  if (!passwordFile) {
    console.error("FRONTEND_AUTH_PASSWORD_FILE is required");
    process.exit(1);
  }

  let password;
  try {
    password = (await readFile(passwordFile, "utf8")).trim();
  } catch {
    console.error("Unable to read frontend authentication secret");
    process.exit(1);
  }

  if (password.length < 32) {
    console.error(
      "Frontend authentication secret must be at least 32 characters",
    );
    process.exit(1);
  }

  const child = spawn(process.execPath, ["server.js"], {
    env: { ...process.env, FRONTEND_AUTH_PASSWORD: password },
    stdio: "inherit",
  });

  for (const signal of ["SIGINT", "SIGTERM"]) {
    process.on(signal, () => child.kill(signal));
  }

  child.on("error", (error) => {
    console.error("Unable to start frontend server", error.message);
    process.exitCode = 1;
  });
  child.on("exit", (code, signal) => {
    process.exitCode = code ?? (signal ? 1 : 0);
  });
}

void main();
