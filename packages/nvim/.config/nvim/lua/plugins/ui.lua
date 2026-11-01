return {
  {
    "nvim-lualine/lualine.nvim",
    opts = {
      options = { theme = "auto", icons_enabled = false, component_separators = "|", section_separators = "" },
    },
  },
  { "folke/which-key.nvim", event = "VeryLazy", opts = { icons = { mappings = false } } },
}
