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
    "tool.execute.before": async (input, output) => {
      if (input.tool !== "bash" || typeof output.args.command !== "string") return;
      if (!/^git\s+push(?:\s|$)/.test(output.args.command)) return;

      const branch = await currentBranch(directory);
      const targetsProtectedBranch = branch && pushTargetsProtectedBranch(output.args.command, branch);

      if (targetsProtectedBranch !== false) {
        throw new Error(
          "Blocked unsafe git push. Only simple, non-force pushes to non-main/master branches are permitted.",
        );
      }
    },
  };
}) satisfies Plugin;
