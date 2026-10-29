local M = {}
local root = vim.fn.stdpath("data") .. "/nvim-work/lazy"
local manager = root .. "/lazy.nvim"
local lazy_commit = "85c7ff3711b730b4030d03144f6db6375044ae82"
local configured = false

local function bootstrap()
  if vim.uv.fs_stat(manager .. "/lua/lazy/init.lua") then return true end
  if vim.fn.executable("git") ~= 1 then
    vim.notify("Lazy bootstrap requires Git; basic editing is still available", vim.log.levels.WARN)
    return false
  end
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
    vim.notify("Lazy bootstrap failed; check Git/network access and restart Neovim:\n"
      .. (result.stderr or ""), vim.log.levels.WARN)
    return false
  end
  assert(vim.uv.fs_rename(staging, manager))
  return true
end

local function configure()
  if configured then return true end
  if not bootstrap() then return false end
  vim.opt.rtp:prepend(manager)
  local state = vim.fn.stdpath("state") .. "/nvim-work"
  vim.fn.mkdir(state, "p")
  require("lazy").setup({
    { "folke/lazy.nvim", branch = "main", commit = lazy_commit },
    {
      "neovim/nvim-lspconfig",
      commit = "4b2b045b8ceb035f5c8bc9cab19b95706bfa6a19",
      lazy = false,
      dependencies = {
        {
          "mason-org/mason.nvim",
          commit = "2a6940af80375532e5e9e7c1f2fc6319a1b7a69d",
          opts = { install_root_dir = vim.fn.stdpath("data") .. "/nvim-work/mason" },
        },
      },
      config = function() require("work.lsp").setup() end,
    },
    {
      "neanias/everforest-nvim",
      commit = "a0e9edc57379e8feafc6ba207c26dbb12fc1b6d8",
      lazy = false,
      priority = 1000,
      dependencies = {
        { "ellisonleao/gruvbox.nvim", commit = "154eb5ff5b96d0641307113fa385eaf0d36d9796" },
      },
      config = function() require("work.theme").setup() end,
    },
    {
      "nvim-tree/nvim-tree.lua",
      commit = "96b6d0ea594a1e519abd58fd8b60a39a9dec1869",
      cmd = { "NvimTreeToggle", "NvimTreeFindFileToggle" },
      keys = {
        { "<leader>fe", "<cmd>NvimTreeFindFileToggle<CR>", desc = "Toggle file tree" },
      },
      opts = {
        git = { enable = false },
        filters = { dotfiles = false, custom = { "^\\.git$" } },
        renderer = {
          icons = {
            show = {
              file = false, folder = false, folder_arrow = false, git = false,
              modified = false, diagnostics = false, bookmarks = false,
            },
          },
        },
      },
    },
    {
      "nvim-telescope/telescope.nvim",
      commit = "a0bbec21143c7bc5f8bb02e0005fa0b982edc026", -- 0.1.8
      lazy = true,
      dependencies = {
        { "nvim-lua/plenary.nvim", commit = "74b06c6c75e4eeb3108ec01852001636d85a932b" },
      },
      opts = {
        defaults = {
          file_sorter = function() return require("work.file_sorter").new() end,
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
    local_spec = false,
    state = state .. "/lazy-state.json",
    pkg = { cache = state .. "/pkg-cache.lua" },
    readme = { root = state .. "/readme" },
    checker = { enabled = false },
    change_detection = { enabled = false },
    rocks = { enabled = false },
  })
  configured = true
  return true
end

function M.setup()
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
      if not configured or not vim.uv.fs_stat(root .. "/telescope.nvim/lua/telescope/init.lua")
          or not vim.uv.fs_stat(root .. "/plenary.nvim/lua/plenary/init.lua") then
        vim.notify("Use :Lazy to install missing plugins; if Lazy is unavailable, check Git/network access and restart", vim.log.levels.WARN)
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
