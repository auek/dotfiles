-- Native commenting covers the baseline without a separate parser integration.
return {
  { "windwp/nvim-autopairs", event = "InsertEnter", opts = {} },
  { "windwp/nvim-ts-autotag", lazy = false, opts = {} },
  { "tpope/vim-surround", event = "BufReadPost", dependencies = { "tpope/vim-repeat" } },
}
