local M = {}

function M.setup()
  local settings = require("config.settings")
  vim.lsp.config("*", { capabilities = require("cmp_nvim_lsp").default_capabilities() })
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
  -- ShellCheck is discovered on PATH by bash-language-server. Formatting is
  -- deliberately disabled even when a machine happens to have shfmt installed.
  vim.lsp.config("bashls", { settings = { bashIde = { shfmt = { path = "" } } } })
  for name, options in pairs(settings.server_options) do vim.lsp.config(name, options) end
  -- Some upstream configs use callable commands to prefer project-local tools.
  -- Check their executable without replacing those upstream launch functions.
  local executables = {
    ts_ls = "typescript-language-server", cssls = "vscode-css-language-server",
    yamlls = "yaml-language-server", bashls = "bash-language-server",
    pyright = "pyright-langserver", lua_ls = "lua-language-server",
    ansiblels = "ansible-language-server",
    astro = "astro-ls", marksman = "marksman",
  }
  local function enable_available()
    for server, enabled in pairs(settings.servers) do
      -- ESLint diagnostics use the project CLI via features.eslint, never a
      -- separately installed language server with its own resolution fallbacks.
      local config = enabled and server ~= "eslint" and vim.lsp.config[server]
      local executable = config and (type(config.cmd) == "table" and config.cmd[1] or executables[server])
      if executable and vim.fn.executable(executable) == 1 then
        vim.lsp.enable(server)
      end
    end
  end
  enable_available()
  -- Installing from :Mason also enables the server for already-open buffers.
  require("mason-registry"):on("package:install:success", vim.schedule_wrap(enable_available))

  local group = vim.api.nvim_create_augroup("DotfilesLsp", { clear = true })
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
