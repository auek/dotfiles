return {
  "nvim-treesitter/nvim-treesitter",
  event = { "BufReadPost", "BufNewFile" },
  cmd = { "InstallParsers", "TSInstall", "TSUpdate", "TSInstallInfo" },
  config = function()
    local parsers = require("config.settings").parsers
    local directory = vim.fn.stdpath("data") .. "/treesitter"
    vim.fn.mkdir(directory, "p")
    vim.opt.runtimepath:prepend(directory)
    require("nvim-treesitter.configs").setup({
      parser_install_dir = directory,
      ensure_installed = {},
      auto_install = false,
      highlight = {
        enable = true,
        disable = function(language)
          -- Retain the verified workaround for Neovim 0.12 Markdown crashes.
          return language == "markdown" or language == "markdown_inline"
            or not vim.tbl_contains(parsers, language)
        end,
      },
    })
    vim.api.nvim_create_user_command("InstallParsers", function()
      if #parsers > 0 then vim.cmd("TSInstall " .. table.concat(parsers, " ")) end
    end, { desc = "Install the explicitly selected Treesitter parsers" })
  end,
}
