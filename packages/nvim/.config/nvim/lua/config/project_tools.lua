local M = {}

-- A repository is the workspace boundary, including monorepos and submodules.
-- Outside Git, stay within the nearest package rather than borrowing tools
-- from an unrelated ancestor directory.
function M.root(filename)
  if not filename or filename == "" then return end
  local directory = vim.fs.dirname(filename)
  return vim.fs.root(directory, ".git") or vim.fs.root(directory, "package.json") or directory
end

function M.find_file(filename, name)
  local root = M.root(filename)
  if not root then return end
  return vim.fs.find(name, {
    path = vim.fs.dirname(filename), upward = true, stop = vim.fs.dirname(root),
  })[1]
end

function M.executable(filename, tool)
  local root = M.root(filename)
  if not root then return end
  local directory = vim.fs.dirname(filename)
  local executable = tool .. (vim.fn.has("win32") == 1 and ".cmd" or "")
  while directory do
    local path = vim.fs.joinpath(directory, "node_modules", ".bin", executable)
    if vim.fn.executable(path) == 1 then return path end
    if directory == root then break end
    directory = vim.fs.dirname(directory)
  end
end

function M.cwd(filename)
  local manifest = M.find_file(filename, "package.json")
  return manifest and vim.fs.dirname(manifest) or M.root(filename)
end

return M
