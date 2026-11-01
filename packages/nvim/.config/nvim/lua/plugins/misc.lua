-- Native commenting covers the baseline without a separate parser integration.
return {
  { "windwp/nvim-autopairs", event = "InsertEnter", opts = {} },
  { "tpope/vim-surround", event = "BufReadPost", dependencies = { "tpope/vim-repeat" } },
}
