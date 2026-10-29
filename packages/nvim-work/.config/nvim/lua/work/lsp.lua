local M = {}

function M.setup()
  -- nvim-lspconfig supplies defaults; Mason only installs tools on request.
  vim.lsp.config("yamlls", {
    settings = {
      redhat = { telemetry = { enabled = false } },
      yaml = {
        format = { enable = false },
        schemaStore = { enable = false, url = "" },
        schemas = {
          ["https://raw.githubusercontent.com/microsoft/azure-pipelines-vscode/master/service-schema.json"] = {
            "azure-pipelines*.yml", "azure-pipelines*.yaml",
            ".azure-pipelines/**/*.yml", ".azure-pipelines/**/*.yaml",
          },
        },
      },
    },
  })
  local executables = {
    ts_ls = "typescript-language-server",
    cssls = "vscode-css-language-server",
    yamlls = "yaml-language-server",
  }
  local function enable_available()
    for server, executable in pairs(executables) do
      if vim.fn.executable(executable) == 1 then vim.lsp.enable(server) end
    end
  end
  enable_available()
  -- Installing from :Mason also enables the server for already-open buffers.
  require("mason-registry"):on("package:install:success", vim.schedule_wrap(enable_available))

  local group = vim.api.nvim_create_augroup("NvimWorkLsp", { clear = true })
  vim.api.nvim_create_autocmd("LspAttach", {
    group = group,
    callback = function(event)
      local function map(lhs, rhs, desc)
        vim.keymap.set("n", lhs, rhs, { buffer = event.buf, silent = true, desc = desc })
      end
      map("gd", vim.lsp.buf.definition, "Go to definition")
      map("gh", vim.lsp.buf.hover, "Hover documentation")
      map("<leader>cr", vim.lsp.buf.rename, "Rename symbol")
      map("<leader>ca", vim.lsp.buf.code_action, "Code actions")
      map("<leader>d", vim.diagnostic.open_float, "Show diagnostic")
      map("[d", function() vim.diagnostic.jump({ count = -1, float = true }) end, "Previous diagnostic")
      map("]d", function() vim.diagnostic.jump({ count = 1, float = true }) end, "Next diagnostic")
    end,
  })
end

return M
