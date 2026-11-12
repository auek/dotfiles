return {
  "stevearc/resession.nvim",
  enabled = require("config.settings").features.session_recovery,
  lazy = false,
  config = function() require("config.sessions").setup() end,
}
