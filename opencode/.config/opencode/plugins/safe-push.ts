import { execFile } from "node:child_process";
import { promisify } from "node:util";
import type { Plugin } from "@opencode-ai/plugin";

const execFileAsync = promisify(execFile);
const protectedBranches = new Set(["main", "master"]);
const upstreamOptions = new Set(["-u", "--set-upstream"]);

async function currentBranch(directory: string) {
  try {
    const { stdout } = await execFileAsync("git", ["branch", "--show-current"], {
      cwd: directory,
      encoding: "utf8",
    });
    return stdout.trim() || undefined;
  } catch {
    return undefined;
  }
}

function pushTargetsProtectedBranch(command: string, branch: string) {
  if (protectedBranches.has(branch)) return true;

  if (
    !/^git\s+push(?:\s|$)/.test(command) ||
    /[;&|`$<>"'\\\n]/.test(command) ||
    /(?:^|\s)(?:-f|--force|--force-with-lease|--force-if-includes|--all|--mirror|--tags)(?:\s|$)/.test(command)
  ) {
    return undefined;
  }

  const args = command.trim().split(/\s+/).slice(2);
  if (args.some((arg) => arg.startsWith("-") && !upstreamOptions.has(arg))) return undefined;

  const pushArgs = args.filter((arg) => !upstreamOptions.has(arg));

  if (pushArgs.length <= 1) return false;

  return pushArgs.slice(1).some((refspec) => {
    const target = (refspec.includes(":") ? refspec.split(":").at(-1) : refspec)
      .replace(/^refs\/heads\//, "");
    return protectedBranches.has(target);
  });
}

export default (async ({ directory }) => {
  return {
    "permission.ask": async (input, output) => {
      if (input.type !== "bash" || typeof input.pattern !== "string") return;

      const branch = await currentBranch(directory);
      if (!branch) return;

      const targetsProtectedBranch = pushTargetsProtectedBranch(input.pattern, branch);
      if (targetsProtectedBranch === true) {
        output.status = "deny";
      } else if (targetsProtectedBranch === false) {
        output.status = "allow";
      }
    },
  };
}) satisfies Plugin;
