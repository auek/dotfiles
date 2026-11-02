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
  {
    "folke/trouble.nvim",
    cmd = "Trouble",
    keys = {
      { "<leader>xx", "<cmd>Trouble diagnostics toggle<CR>", desc = "Diagnostics (Trouble)" },
      { "<leader>xX", "<cmd>Trouble diagnostics toggle filter.buf=0<CR>", desc = "Buffer diagnostics (Trouble)" },
      { "<leader>xQ", "<cmd>Trouble qflist toggle<CR>", desc = "Quickfix list (Trouble)" },
      { "<leader>xL", "<cmd>Trouble loclist toggle<CR>", desc = "Location list (Trouble)" },
    },
    opts = {
      win = { position = "bottom" },
      -- Keep every mode usable without a patched font or an icon provider.
      icons = {
        indent = { fold_open = "v ", fold_closed = "> " },
        folder_closed = "", folder_open = "",
      },
      formatters = {
        file_icon = function() return "" end,
        kind_icon = function() return "" end,
        severity_icon = function(ctx) return require("trouble.format").formatters.severity(ctx) end,
      },
    },
  },
}
