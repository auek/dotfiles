local M = {}
local root = vim.fn.stdpath("data") .. "/nvim-work/lazy"
local manager = root .. "/lazy.nvim"
local lazy_commit = "85c7ff3711b730b4030d03144f6db6375044ae82"
local configured = false

local function configure()
  if configured then return true end
  if not vim.uv.fs_stat(manager .. "/lua/lazy/init.lua") then return false end
  vim.opt.rtp:prepend(manager)
  local state = vim.fn.stdpath("state") .. "/nvim-work"
  vim.fn.mkdir(state, "p")
  require("lazy").setup({
    { "folke/lazy.nvim", branch = "main", commit = lazy_commit },
    {
      "nvim-telescope/telescope.nvim",
      commit = "a0bbec21143c7bc5f8bb02e0005fa0b982edc026", -- 0.1.8
      lazy = true,
      dependencies = {
        { "nvim-lua/plenary.nvim", commit = "74b06c6c75e4eeb3108ec01852001636d85a932b" },
      },
      opts = {
        defaults = {
          -- Include project dotfiles, while respecting ignores and excluding Git metadata.
          vimgrep_arguments = {
            "rg", "--color=never", "--no-heading", "--with-filename",
            "--line-number", "--column", "--smart-case", "--hidden", "--glob", "!.git/**",
          },
          file_ignore_patterns = { "^%.git/" },
        },
        pickers = { find_files = { hidden = true } },
      },
    },
  }, {
    root = root,
    lockfile = state .. "/lazy-lock.json",
    install = { missing = false },
    checker = { enabled = false },
    change_detection = { enabled = false },
    rocks = { enabled = false },
  })
  configured = true
  return true
end

local function install()
  if vim.fn.executable("git") ~= 1 then
    vim.notify("WorkPluginsInstall requires Git", vim.log.levels.WARN)
    return
  end
  if not vim.uv.fs_stat(manager) then
    vim.fn.mkdir(root, "p")
    local staging = assert(vim.uv.fs_mkdtemp(root .. "/.lazy-install-XXXXXX"))
    local result = vim.system({
      "git", "clone", "--filter=blob:none", "--branch=stable",
      "https://github.com/folke/lazy.nvim.git", staging,
    }, { text = true }):wait()
    if result.code == 0 then
      result = vim.system({ "git", "-C", staging, "checkout", lazy_commit }, { text = true }):wait()
    end
    if result.code ~= 0 then
      vim.fn.delete(staging, "rf")
      vim.notify("Lazy installation failed: " .. (result.stderr or ""), vim.log.levels.ERROR)
      return
    end
    assert(vim.uv.fs_rename(staging, manager))
  end
  if configure() then
    require("lazy").install({ wait = true })
  else
    vim.notify("Incomplete Lazy installation at " .. manager, vim.log.levels.ERROR)
  end
end

function M.setup()
  vim.api.nvim_create_user_command("WorkPluginsInstall", install, {
    desc = "Install the work profile's pinned Lazy, Telescope, and Plenary",
  })
  configure()
  local pickers = {
    ["<leader>ff"] = { "find_files", "Find project files" },
    ["<leader>fg"] = { "live_grep", "Search project text" },
    ["<leader>fo"] = { "oldfiles", "Recent files" },
    ["<leader>ls"] = { "buffers", "Find buffers" },
    ["<leader>fh"] = { "help_tags", "Search help" },
  }
  for key, picker in pairs(pickers) do
    vim.keymap.set("n", key, function()
      if not configure() or not vim.uv.fs_stat(root .. "/telescope.nvim/lua/telescope/init.lua")
          or not vim.uv.fs_stat(root .. "/plenary.nvim/lua/plenary/init.lua") then
        vim.notify("Run :WorkPluginsInstall to install the work navigation plugins", vim.log.levels.WARN)
        return
      end
      if picker[1] == "live_grep" and vim.fn.executable("rg") ~= 1 then
        vim.notify("Project text search requires ripgrep (rg) on PATH", vim.log.levels.WARN)
        return
      end
      require("telescope.builtin")[picker[1]]()
    end, { silent = true, desc = picker[2] })
  end
end

return M
