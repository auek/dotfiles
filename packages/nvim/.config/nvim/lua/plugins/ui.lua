return {
  {
    "folke/snacks.nvim",
    lazy = false,
    priority = 1000,
    opts = function() return require("config.dashboard").options() end,
    config = function(_, opts)
      require("snacks").setup(opts)
      require("config.dashboard").highlights()
    end,
  },
  {
    "nvim-lualine/lualine.nvim",
    opts = {
      options = {
        theme = "auto", icons_enabled = false, component_separators = "|", section_separators = "",
        disabled_filetypes = { statusline = { "snacks_dashboard" } },
      },
    },
  },
  { "folke/which-key.nvim", event = "VeryLazy", opts = { icons = { mappings = false } } },
}
