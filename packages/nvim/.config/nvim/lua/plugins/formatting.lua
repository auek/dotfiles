local prettier_filetypes = {
  "javascript", "javascriptreact", "typescript", "typescriptreact",
  "css", "scss", "less", "json", "jsonc", "yaml", "html", "markdown", "markdown.mdx", "graphql",
}
local formatters_by_ft = {}
for _, filetype in ipairs(prettier_filetypes) do formatters_by_ft[filetype] = { "prettier" } end

return {
  {
    "stevearc/conform.nvim",
    enabled = require("config.settings").features.format_on_save,
    event = "BufWritePre",
    opts = {
      formatters_by_ft = formatters_by_ft,
      formatters = {
        prettier = {
          command = function(_, ctx)
            local tools = require("config.project_tools")
            local executable = vim.fn.has("win32") == 1 and "prettier.cmd" or "prettier"
            -- An absolute missing path prevents any fallback to PATH or cwd.
            return tools.executable(ctx.filename, "prettier")
              or vim.fs.joinpath(tools.root(ctx.filename), "node_modules", ".bin", executable)
          end,
          cwd = function(_, ctx)
            return require("config.project_tools").cwd(ctx.filename)
          end,
          prepend_args = function(_, ctx)
            local ignore = require("config.project_tools").find_file(ctx.filename, ".prettierignore")
            return ignore and { "--ignore-path", ignore } or {}
          end,
        },
      },
      format_on_save = function(buffer)
        local filetype = vim.bo[buffer].filetype
        if filetype == "sh" or filetype == "bash" then return end
        if vim.tbl_contains(prettier_filetypes, filetype) then
          if not require("conform").get_formatter_info("prettier", buffer).available then return end
          return { lsp_format = "never", timeout_ms = require("config.settings").format_timeout_ms }
        end
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
