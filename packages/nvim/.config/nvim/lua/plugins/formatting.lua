return {
  {
    "stevearc/conform.nvim",
    version = "*", -- Pin to stable releases
    opts = {
      formatters_by_ft = {
        lua = { "stylua" },
        sh = { "shfmt" },
        bash = { "shfmt" },
        python = { "black" },
      },
      format_on_save = {
        lsp_fallback = true,
        async = false,
        timeout_ms = 500,
      },
    },
  },

  -- Auto pairs and tags
  { "windwp/nvim-autopairs", config = true },

  -- Surround
  { "tpope/vim-surround" },
  { "tpope/vim-repeat" },
}
