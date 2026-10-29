-- A standalone alternative to the home nvim package.
vim.g.mapleader = " "
local opt = vim.opt
opt.guicursor = "i:ver100-iCursor"
opt.number = true
opt.relativenumber = true
opt.tabstop = 2
opt.softtabstop = 2
opt.shiftwidth = 2
opt.expandtab = true
opt.autoindent = true
opt.smartindent = true
opt.ignorecase = true
opt.smartcase = true
opt.incsearch = true
opt.hlsearch = false
opt.wrap = false
opt.signcolumn = "yes:1"
opt.termguicolors = true
-- Clipboard work is explicit: ordinary yanks/deletes stay in normal registers.
opt.clipboard = ""
vim.cmd("filetype plugin indent on")
vim.cmd("syntax enable")
vim.cmd.colorscheme("habamax")

local map = function(mode, lhs, rhs)
  vim.keymap.set(mode, lhs, rhs, { silent = true })
end
map("i", "jj", "<Esc>")
for _, direction in ipairs({ "h", "j", "k", "l" }) do
  map("n", "<C-" .. direction .. ">", "<C-w>" .. direction)
end
map("n", "<leader>w", "<cmd>write<CR>")
map("n", "<leader>q", "<cmd>quit<CR>")
map("n", "<C-n>", "<cmd>bnext<CR>")
map("n", "<C-p>", "<cmd>bprevious<CR>")
map("x", "<leader>y", '"*y')
map("n", "<leader>p", '"*p')
map("n", "<leader>b", function()
  local current = vim.api.nvim_get_current_buf()
  if vim.bo[current].modified then
    vim.notify("Unsaved changes; write the buffer before closing it", vim.log.levels.WARN)
    return
  end
  local replacement = vim.fn.bufnr("#")
  if replacement == current or not vim.api.nvim_buf_is_valid(replacement)
      or not vim.bo[replacement].buflisted then
    replacement = nil
    for _, buf in ipairs(vim.api.nvim_list_bufs()) do
      if buf ~= current and vim.bo[buf].buflisted then
        replacement = buf
        break
      end
    end
  end
  replacement = replacement or vim.api.nvim_create_buf(true, false)
  for _, win in ipairs(vim.fn.win_findbuf(current)) do
    vim.api.nvim_win_set_buf(win, replacement)
  end
  vim.api.nvim_buf_delete(current, { force = false })
end)
for _, name in ipairs({ "W", "Wq", "WQ" }) do
  vim.api.nvim_create_user_command(name, name == "W" and "write" or "wq", {})
end

-- No Windows process is started until an explicit clipboard operation.
-- PowerShell reads UTF-8 stdin; clipboard text never becomes executable code.
if vim.fn.has("wsl") == 1 and vim.fn.executable("powershell.exe") == 1 then
  local function powershell(script, input)
    local result = vim.system({
      "powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", script,
    }, { stdin = input, text = false }):wait(5000)
    if result.code ~= 0 then
      error("Windows clipboard operation failed: " .. (result.stderr or ""))
    end
    return result.stdout or ""
  end
  local function copy(lines)
    -- Neovim already includes a final empty line for linewise selections.
    local text = table.concat(lines, "\n")
    powershell(
      "$ErrorActionPreference = 'Stop'; "
        .. "[Console]::InputEncoding = New-Object System.Text.UTF8Encoding($false); "
        .. "Set-Clipboard -Value ([Console]::In.ReadToEnd())", text)
  end
  local function paste()
    local text = powershell(
      "$ErrorActionPreference = 'Stop'; "
        .. "[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false); "
        .. "$text = Get-Clipboard -Raw; if ($null -ne $text) { [Console]::Out.Write($text) }")
    return { vim.split(text:gsub("\r\n", "\n"), "\n", { plain = true }), "v" }
  end
  vim.g.clipboard = {
    name = "WSL Windows clipboard",
    copy = { ["+"] = copy, ["*"] = copy },
    paste = { ["+"] = paste, ["*"] = paste },
    cache_enabled = 0,
  }
end

opt.autoread = true
local reload = vim.api.nvim_create_augroup("NvimWorkReload", { clear = true })
local function check_current_file()
  -- Skip modified buffers entirely to avoid conflict prompts and lost edits.
  if vim.fn.mode() == "n" and vim.fn.getcmdtype() == "" and not vim.bo.modified
      and vim.bo.buftype == "" then
    vim.cmd("checktime " .. vim.api.nvim_get_current_buf())
  end
end
vim.api.nvim_create_autocmd({ "FocusGained", "BufEnter", "CursorHold" }, {
  group = reload,
  callback = check_current_file,
})
vim.api.nvim_create_autocmd({ "InsertLeave", "CmdlineLeave" }, {
  group = reload,
  callback = function() vim.schedule(check_current_file) end,
})
local wrap = vim.api.nvim_create_augroup("NvimWorkWrap", { clear = true })
vim.api.nvim_create_autocmd("FileType", {
  group = wrap,
  pattern = { "markdown", "text" },
  callback = function()
    vim.opt_local.wrap = true
    vim.opt_local.linebreak = true
  end,
})

require("work.plugins").setup()
