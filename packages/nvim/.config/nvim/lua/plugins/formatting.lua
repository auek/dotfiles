return {
  {
    "stevearc/conform.nvim",
    enabled = require("config.settings").features.format_on_save,
    event = "BufWritePre",
    opts = {
      formatters_by_ft = { lua = { "stylua" }, python = { "black" } },
      format_on_save = function(buffer)
        if vim.bo[buffer].filetype == "sh" or vim.bo[buffer].filetype == "bash" then return end
        return { lsp_format = "fallback", timeout_ms = 500 }
      end,
    },
  },
  {
    "iamcco/markdown-preview.nvim",
    enabled = require("config.settings").features.markdown_preview,
    cmd = { "MarkdownPreviewToggle", "MarkdownPreview", "MarkdownPreviewStop" },
    build = "cd app && npm install",
    init = function() vim.g.mkdp_filetypes = { "markdown" } end,
    ft = { "markdown" },
  },
}
