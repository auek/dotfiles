local directory = vim.fn.stdpath("data") .. "/lazy/nvim-treesitter"
local legacy = vim.uv.fs_stat(directory .. "/lua/nvim-treesitter/configs.lua") ~= nil
local ready = vim.fn.has("nvim-0.12") == 1 and not legacy

local spec = {
  "nvim-treesitter/nvim-treesitter",
  lazy = not ready, -- Supported main loads eagerly; an installed legacy copy stays dormant.
  build = ":TSUpdate",
  init = function()
    -- Keep a pull/restart safe before the installed plugin has been updated:
    -- never put legacy 0.11 queries/predicates onto Neovim 0.12's runtimepath.
    if not ready then
      vim.schedule(function()
        vim.notify("Treesitter needs Neovim 0.12+ and the pinned main-branch plugin. "
          .. "Run :Lazy update nvim-treesitter, then restart. Syntax highlighting remains available.", vim.log.levels.WARN)
      end)
    end
  end,
  config = function()
    local parsers = require("config.settings").parsers
    local treesitter = require("nvim-treesitter")
    -- Separate the supported parser/query set from untouched legacy artifacts.
    treesitter.setup({ install_dir = vim.fn.stdpath("data") .. "/treesitter-v2" })
    local function highlight(buffer)
      if not vim.api.nvim_buf_is_valid(buffer) then return end
      local language = vim.treesitter.language.get_lang(vim.bo[buffer].filetype)
      if language and vim.tbl_contains(parsers, language) then
        local available, parser = pcall(vim.treesitter.get_parser, buffer, language)
        if available and parser then vim.treesitter.start(buffer, language) end
      end
    end
    local group = vim.api.nvim_create_augroup("DotfilesTreesitter", { clear = true })
    vim.api.nvim_create_autocmd({ "FileType", "BufWinEnter" }, {
      group = group,
      callback = function(event) highlight(event.buf) end,
    })
    highlight(vim.api.nvim_get_current_buf())
    vim.api.nvim_create_user_command("InstallParsers", function()
      if #parsers == 0 then return end
      if vim.fn.executable("tree-sitter") == 0 then
        vim.notify("Parser installation needs standalone tree-sitter CLI 0.26.1+; see README Neovim setup.", vim.log.levels.WARN)
        return
      end
      local result = vim.system({ "tree-sitter", "--version" }, { text = true }):wait()
      local version = result.code == 0 and vim.version.parse(result.stdout)
      if not version or not vim.version.ge(version, { 0, 26, 1 }) then
        vim.notify("Parser installation needs tree-sitter CLI 0.26.1+.", vim.log.levels.WARN)
        return
      end
      treesitter.install(parsers):await(vim.schedule_wrap(function(err, installed)
        if err or not installed then
          vim.notify("Parser installation failed; inspect :TSLog.", vim.log.levels.WARN)
          return
        end
        for _, buffer in ipairs(vim.api.nvim_list_bufs()) do highlight(buffer) end
      end))
    end, { desc = "Install the explicitly selected Treesitter parsers" })
  end,
}
-- Keep the plugin in Lazy's update list, but prevent automatic module loading
-- from activating its old scripts before :Lazy update replaces them.
if not ready then spec.module = false end
return spec
