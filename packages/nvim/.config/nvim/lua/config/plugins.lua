local M = {}
local root = vim.fn.stdpath("data") .. "/lazy"
local manager = root .. "/lazy.nvim"
local pins = vim.json.decode(table.concat(vim.fn.readfile(vim.fn.stdpath("config") .. "/lazy-lock.json"), "\n"))
local lazy_commit = pins["lazy.nvim"].commit
local configured = false

-- One tracked set of pins for every machine. Lazy writes its runtime lockfile
-- to local state, not through a Stow symlink into the repository.
local function pin(spec)
  if type(spec) == "string" then spec = { spec } end
  if type(spec[1]) == "string" then
    local name = spec[1]:match("/([^/]+)$")
    spec.commit = assert(pins[name], "Missing plugin pin: " .. name).commit
  end
  for index, child in ipairs(spec) do
    if type(child) == "table" then spec[index] = pin(child) end
  end
  for index, dependency in ipairs(spec.dependencies or {}) do spec.dependencies[index] = pin(dependency) end
  return spec
end

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
  local state = vim.fn.stdpath("state") .. "/dotfiles"
  vim.fn.mkdir(state, "p")
  local spec = {
    { "folke/lazy.nvim", branch = "main", commit = lazy_commit },
    {
      "christoomey/vim-tmux-navigator",
      lazy = false,
      init = function() vim.g.tmux_navigator_save_on_switch = 0 end,
    },
    {
      "neovim/nvim-lspconfig",
      lazy = false,
      dependencies = {
        { "mason-org/mason.nvim", opts = { install_root_dir = vim.fn.stdpath("data") .. "/mason" } },
        "hrsh7th/cmp-nvim-lsp",
      },
      config = function() require("config.lsp").setup() end,
    },
    {
      "neanias/everforest-nvim",
      lazy = false,
      priority = 1000,
      dependencies = {
        "ellisonleao/gruvbox.nvim",
      },
      config = function() require("config.theme").setup() end,
    },
    {
      "nvim-tree/nvim-tree.lua",
      cmd = { "NvimTreeToggle", "NvimTreeFindFileToggle" },
      keys = {
        { "<leader>fe", "<cmd>NvimTreeFindFileToggle<CR>", desc = "Toggle file tree" },
      },
      init = function()
        vim.g.loaded_netrw = 1
        vim.g.loaded_netrwPlugin = 1
        local group = vim.api.nvim_create_augroup("DotfilesDirectory", { clear = true })
        vim.api.nvim_create_autocmd("BufEnter", {
          group = group,
          callback = function(event)
            local path = vim.api.nvim_buf_get_name(event.buf)
            if vim.fn.isdirectory(path) == 1 then
              require("nvim-tree.api").tree.open({ path = path })
            end
          end,
        })
      end,
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
      lazy = true,
      dependencies = {
        "nvim-lua/plenary.nvim",
        {
          "nvim-telescope/telescope-fzf-native.nvim",
          build = "make",
        },
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
        extensions = { fzf = { case_mode = "smart_case" } },
      },
      config = function(_, opts)
        require("telescope").setup(opts)
        local ok, err = pcall(require("telescope").load_extension, "fzf")
        if not ok then
          vim.notify("FZF sorter unavailable; run :Lazy build telescope-fzf-native.nvim\n"
            .. tostring(err), vim.log.levels.WARN)
        end
      end,
    },
    require("plugins.completion"),
    require("plugins.git"),
    require("plugins.linting"),
    require("plugins.treesitter"),
    require("plugins.misc"),
    require("plugins.ui"),
    (require("plugins.formatting")),
  }
  require("lazy").setup(pin(spec), {
    root = root,
    lockfile = state .. "/lazy-lock.json",
    local_spec = false,
    state = state .. "/lazy-state.json",
    pkg = { cache = state .. "/pkg-cache.lua" },
    readme = { root = state .. "/readme" },
    checker = { enabled = false },
    install = { missing = true },
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
    ["<leader>fF"] = { "find_files", "Find all project files", { hidden = true, no_ignore = true } },
    ["<leader>fG"] = { "live_grep", "Search all project text", { additional_args = { "--hidden", "--no-ignore" } } },
    ["<C-f>"] = { "command_history", "Search command history", nil, "c" },
  }
  for key, picker in pairs(pickers) do
    vim.keymap.set(picker[4] or "n", key, function()
      if not configured or not vim.uv.fs_stat(root .. "/telescope.nvim/lua/telescope/init.lua")
          or not vim.uv.fs_stat(root .. "/plenary.nvim/lua/plenary/init.lua") then
        vim.notify("Use :Lazy to install missing plugins; if Lazy is unavailable, check Git/network access and restart", vim.log.levels.WARN)
        return
      end
      if picker[1] == "live_grep" and vim.fn.executable("rg") ~= 1 then
        vim.notify("Project text search requires ripgrep (rg) on PATH", vim.log.levels.WARN)
        return
      end
      require("telescope.builtin")[picker[1]](picker[3])
    end, { silent = true, desc = picker[2] })
  end
end

return M
