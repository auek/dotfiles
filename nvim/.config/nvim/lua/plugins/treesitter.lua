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
          "markdown",
          "markdown_inline",
          "python",
          "scss",
          "tsx",
          "typescript",
          "yaml",
        },
        highlight = {
          enable = true,
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
