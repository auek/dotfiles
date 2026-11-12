local M = {}
local uv = vim.uv
local directory = "dotfiles/recovery"
local root = vim.fn.stdpath("data") .. "/" .. directory
local name, lock, timer
local started, stopped, stdin = false, false, false

local function warn(message)
  vim.notify_once("Session recovery: " .. message, vim.log.levels.WARN)
end

local function read(path)
  local ok, lines = pcall(vim.fn.readfile, path)
  return ok and table.concat(lines, "\n") or nil
end

local function process_start(pid)
  local stat = read("/proc/" .. pid .. "/stat")
  local fields = stat and stat:match("^.*%) (.*)")
  return fields and vim.split(fields, " ")[20] -- Linux start-time ticks (field 22).
end

local function identity()
  if vim.env.TMUX and vim.env.TMUX_PANE then
    -- Pane IDs change after resurrect; names and layout indices are restored.
    local result = vim.system({ "tmux", "display-message", "-p", "-t", vim.env.TMUX_PANE,
      "#{socket_path}\t#{session_name}\t#{window_index}\t#{pane_index}" }, { text = true }):wait(1000)
    if result.code ~= 0 or vim.trim(result.stdout or "") == "" then
      error("could not identify this tmux pane; no snapshot will be overwritten")
    end
    return "tmux-" .. vim.fn.sha256(vim.trim(result.stdout))
  end
  local cwd = vim.fn.getcwd(-1, -1)
  return "cwd-" .. vim.fn.sha256(uv.fs_realpath(cwd) or cwd)
end

local function acquire()
  vim.fn.mkdir(root, "p", 448) -- 0700; private, machine-local state.
  local path = root .. "/" .. name .. ".lock"
  local boot = read("/proc/sys/kernel/random/boot_id")
  local fd = uv.fs_open(path, "wx", 384)
  if not fd then
    local ok, owner = pcall(vim.json.decode, read(path) or "")
    if ok and type(owner) == "table" and type(owner.pid) == "number" and owner.pid > 0 and owner.pid % 1 == 0 then
      local _, _, code = uv.kill(owner.pid, 0)
      local start = process_start(owner.pid)
      if (boot and owner.boot and boot ~= owner.boot) or code == "ESRCH"
          or (start and owner.start and start ~= owner.start) then
        uv.fs_unlink(path)
        fd = uv.fs_open(path, "wx", 384)
      end
    end
  end
  if not fd then
    error("another editor owns this pane/directory snapshot (or its lock is unreadable)")
  end
  lock = path
  local pid = vim.fn.getpid()
  local written, err = uv.fs_write(fd, vim.json.encode({ pid = pid, boot = boot, start = process_start(pid) }))
  if written then uv.fs_fsync(fd) end
  uv.fs_close(fd)
  assert(written, err)
end

local function has_files()
  for _, buf in ipairs(vim.api.nvim_list_bufs()) do
    if vim.bo[buf].buflisted and vim.bo[buf].buftype == "" and vim.api.nvim_buf_get_name(buf) ~= "" then
      return true
    end
  end
  return false
end

function M.save()
  if not started or stopped or not has_files() then return false end
  local pending = name .. ".pending-" .. vim.fn.getpid()
  local temporary = root .. "/" .. pending .. ".json"
  local eventignore = vim.o.eventignore
  local ok, err = pcall(function()
    require("resession").save(pending, { dir = directory, notify = false, attach = false })
    -- Resession writes in place. Only publish a fully written snapshot.
    local fd = assert(uv.fs_open(temporary, "r+", 384))
    local synced, sync_err = uv.fs_fsync(fd)
    uv.fs_close(fd)
    assert(synced, sync_err)
    assert(uv.fs_rename(temporary, root .. "/" .. name .. ".json"))
    -- Persist the rename too where directory fsync is supported (including WSL).
    local parent = uv.fs_open(root, "r", 448)
    if parent then uv.fs_fsync(parent); uv.fs_close(parent) end
  end)
  vim.o.eventignore = eventignore
  uv.fs_unlink(temporary)
  if not ok then warn("save failed; previous snapshot retained: " .. tostring(err)) end
  return ok
end

function M.restore()
  if not started then return false end
  for _, buf in ipairs(vim.api.nvim_list_bufs()) do
    if vim.bo[buf].modified then
      warn("write or discard modified buffers before restoring")
      return false
    end
  end
  local path = root .. "/" .. name .. ".json"
  if vim.fn.filereadable(path) ~= 1 then return true end
  local eventignore, shortmess = vim.o.eventignore, vim.o.shortmess
  local ok, err = pcall(require("resession").load, name, { dir = directory, silence_errors = false })
  vim.o.eventignore, vim.o.shortmess = eventignore, shortmess
  if not ok then
    stopped = true -- Never autosave a partial restoration over the recoverable file.
    warn("restore failed; automatic saves stopped and snapshot retained: " .. tostring(err))
  end
  return ok
end

function M.stop()
  stopped = true
  if timer then timer:stop() end
end

function M.setup()
  if M.configured then return end
  M.configured = true
  require("resession").setup({
    dir = directory,
    autosave = { enabled = false }, -- Our timer saves through an atomic replacement.
    buf_filter = function(buf)
      return vim.bo[buf].buflisted and vim.bo[buf].buftype == "" and vim.api.nvim_buf_get_name(buf) ~= ""
    end,
  })
  local group = vim.api.nvim_create_augroup("DotfilesSessions", { clear = true })
  vim.api.nvim_create_autocmd("StdinReadPre", { group = group, callback = function() stdin = true end })
  vim.api.nvim_create_autocmd("VimEnter", {
    group = group, once = true,
    callback = function()
      vim.schedule(function()
        -- Headless jobs, piped input and explicit -S sessions must keep their own lifecycle.
        if #vim.api.nvim_list_uis() == 0 or stdin or vim.v.this_session ~= ""
            or vim.tbl_contains(vim.v.argv, "-S") then return end
        local ok, err = pcall(function() name = identity(); acquire() end)
        if not ok then warn(tostring(err)); return end
        started = true
        -- Explicit file/directory arguments win; bare nvim resumes this pane.
        if vim.fn.argc() == 0 and not M.restore() then stopped = true; return end
        timer = assert(uv.new_timer())
        local interval = require("config.settings").session_save_interval * 1000
        timer:start(interval, interval, vim.schedule_wrap(M.save))
      end)
    end,
  })
  vim.api.nvim_create_autocmd("VimLeavePre", {
    group = group,
    callback = function()
      M.save()
      if timer then timer:stop(); timer:close(); timer = nil end
      if lock then uv.fs_unlink(lock); lock = nil end
    end,
  })
  for command, callback in pairs({ SessionSave = M.save, SessionRestore = M.restore, SessionStop = M.stop }) do
    vim.api.nvim_create_user_command(command, callback, {})
  end
end

return M
