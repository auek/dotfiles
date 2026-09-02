return {
  {
    "nvim-treesitter/nvim-treesitter",
    version = "*",
    build = ":TSUpdate",
    dependencies = {
      "windwp/nvim-ts-autotag",
      "yioneko/nvim-yati",
    },
    config = function()
      require("nvim-treesitter.configs").setup({
        ensure_installed = {
          "bash",
          "css",
          "dockerfile",
          "html",
          "javascript",
          "json",
          "lua",
          "make",
          "python",
          "scss",
          "tsx",
          "typescript",
          "yaml",
        },
        highlight = {
          enable = true,
          disable = { "markdown", "markdown_inline" },
        },
        yati = {
          enable = true,
        },
      })
    end,
  },

  {
    "pearofducks/ansible-vim"
  }
}
