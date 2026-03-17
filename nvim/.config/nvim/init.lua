vim.g.mapleader = " "

-- Load configurations early
require("config.keymaps")
require("config.options")

-- Clipboard
if vim.fn.has("wsl") then
  vim.g.clipboard = {
    name = "WslClipboard",
    copy = {
      ["+"] = "clip.exe",
      ["*"] = "clip.exe",
    },
    paste = {
      ["+"] =
      'powershell.exe -c [Console]::Out.Write($(Get-Clipboard -Raw).tostring().replace("`r", ""))',
      ["*"] =
      'powershell.exe -c [Console]::Out.Write($(Get-Clipboard -Raw).tostring().replace("`r", ""))',
    },
    cache_enabled = 0,
  }
end

-- TODO: Test this make sure this works
-- Auto-reload file when changed externally
vim.opt.autoread = true
-- Trigger checktime to check for changes on disk
vim.api.nvim_create_autocmd({ "FocusGained", "BufEnter", "CursorHold", "CursorHoldI" }, {
  pattern = "*",
  callback = function()
    if vim.fn.mode() ~= 'c' and not vim.bo.modified then
      vim.cmd("checktime")
    end
  end,
})

-- Notification/Redraw when file changes
vim.api.nvim_create_autocmd("FileChangedShellPost", {
  pattern = "*",
  callback = function()
    vim.notify("File changed on disk. Reloading...", vim.log.levels.INFO)
    vim.cmd("redraw")
  end,
})

-- Wordwrap for markdown and txt files
local wrap_group = vim.api.nvim_create_augroup("WrapSettings", { clear = true })
vim.api.nvim_create_autocmd("FileType", {
  group = wrap_group,
  pattern = { "markdown", "txt" },
  callback = function()
    vim.opt_local.wrap = true
    vim.opt_local.linebreak = true
  end,
})

-- Bootstrap lazy.nvim
local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
if not vim.uv.fs_stat(lazypath) then
  vim.fn.system({
    "git",
    "clone",
    "--filter=blob:none",
    "https://github.com/folke/lazy.nvim.git",
    "--branch=stable",
    lazypath,
  })
end
vim.opt.rtp:prepend(lazypath)

require("lazy").setup("plugins")
